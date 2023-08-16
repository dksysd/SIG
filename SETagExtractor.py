from typing import Any, Union

from mysql.connector import pooling

from src.MorphemeAnalyzer import MorphemeAnalyzer
from src.TagExtractor import TagExtractor


class DatabaseController:
    """
    <데이터베이스 설계>
    CREATE TABLE tag
    (
        id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(20) NOT NULL
    );

    CREATE TABLE post
    (
        id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        title       VARCHAR(255) NOT NULL,
        content     TEXT,
        author      VARCHAR(100) NOT NULL,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE keyword
    (
        id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(20) NOT NULL
    );

    CREATE TABLE tag_post
    (
        tag_id  INT UNSIGNED,
        post_id INT UNSIGNED,
        FOREIGN KEY (tag_id) REFERENCES tag (id),
        FOREIGN KEY (post_id) REFERENCES post (id),
        PRIMARY KEY (tag_id, post_id)
    );

    CREATE TABLE keyword_post
    (
        post_id    INT UNSIGNED,
        keyword_id INT UNSIGNED,
        value      FLOAT,
        FOREIGN KEY (post_id) REFERENCES post (id),
        FOREIGN KEY (keyword_id) REFERENCES keyword (id),
        PRIMARY KEY (post_id, keyword_id, value)
    );

    CREATE TABLE answer_tag_post
    (
        tag_id  INT UNSIGNED,
        post_id INT UNSIGNED,
        FOREIGN KEY (tag_id) REFERENCES tag (id),
        FOREIGN KEY (post_id) REFERENCES post (id),
        PRIMARY KEY (tag_id, post_id)
    );

    CREATE TABLE queue
    (
        id      INT UNSIGNED AUTO_INCREMENT,
        post_id INT UNSIGNED,
        FOREIGN KEY (post_id) REFERENCES post (id),
        PRIMARY KEY (id, post_id)
    );

    """

    def __init__(self, user: str, password: str, host: str, db: str):
        self.connection_pool = pooling.MySQLConnectionPool(pool_reset_session=True, user=user, password=password,
                                                           host=host, database=db, autocommit=True)

    def _execute(self, sql: str, args: Union[tuple, list] = None) -> Any:
        """
        SQL 쿼리 실행
        :return: 결과값
        """
        connection = self.connection_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(operation=sql, params=args)
        result_list = cursor.fetchall()
        connection.close()
        return result_list

    def get_tag_set(self):
        """
        :return: 데이터베이스에 기록되어 있는 기본 태그들
        """
        tag_set = set()
        for result in self._execute(sql='SELECT name FROM tag'):
            tag = result[0]
            tag_set.add(tag)
        return tag_set

    def get_data(self, post_id: int) -> tuple[str, str, str]:
        """
        post_number에 해당하는 정보 반환
        :param post_id: 게시글 번호
        :return: 정보 (제목, 작성자, 게시글)
        """
        result_list = self._execute(
            sql='SELECT title, content, author FROM post WHERE id = (%s)', args=[post_id])
        title = self._none_check(text=result_list[0][0])
        post_text = self._none_check(text=result_list[0][1])
        author = self._none_check(text=result_list[0][2])
        return title, post_text, author

    def save_keywords(self, post_id: int, keyword_list: list[str, float]):
        """
        모든 키워드들 저장
        :param post_id: 해당하는 게시글 번호
        """
        for keyword, value in keyword_list:
            self.save_keyword(post_id=post_id, keyword=keyword, value=value)

    def save_keyword(self, post_id: int, keyword: str, value: float):
        """
        저장되지 않은 키워드의 경우, 키워드를 추가함. 이후 keyword_post 테이블에 해당 키워드와 게시글 관련 정보를 저장함.
        :param post_id: 해당하는 게시글 번호
        :param keyword: 키워드
        :param value: 키워드 가중치
        """
        keyword_id = self._execute(sql='SELECT id FROM keyword WHERE name = (%s)', args=[keyword])
        if keyword_id:
            if type(keyword_id) is list:
                keyword_id = keyword_id[0][0]

            self._execute(sql='INSERT IGNORE INTO keyword_post (keyword_id, value, post_id) VALUES (%s, %s, %s)',
                          args=(keyword_id, value, post_id))
        else:
            self._execute(sql='INSERT IGNORE INTO keyword (name) VALUES (%s)', args=[keyword])
            self.save_keyword(post_id=post_id, keyword=keyword, value=value)

    def save_tags(self, post_id: int, tag_list: list[str]):
        """
        모든 태그들 저장
        :param post_id: 해당하는 게시글 번호
        :return:
        """
        for tag in tag_list:
            self.save_tag(post_id=post_id, tag=tag)

    def save_tag(self, post_id: int, tag: str):
        """
        tag의 ID를 획득하고, 이와 게시글 관련 정보를 tag_post 테이블에 저장
        :param post_id: 해당하는 게시글 번호
        :return:
        """
        tag_id = self._execute(sql='SELECT id FROM tag WHERE name = (%s)', args=[tag])[0][0]
        self._execute(sql='INSERT IGNORE INTO tag_post (tag_id, post_id) VALUES (%s, %s)', args=(tag_id, post_id))

    def _none_check(self, text: str) -> str:
        """
        text가 None일 경우 공백 문자열 반환
        """
        return '' if text is None else text


class SETagExtractor:
    def __init__(self, user: str, password: str, host: str, db: str):
        self.database_controller = DatabaseController(user=user, password=password, host=host, db=db)
        tag_set = self.database_controller.get_tag_set()
        morpheme_analyzer = MorphemeAnalyzer(is_typos=True)
        for tag in tag_set:
            morpheme_analyzer.add_user_word(word=tag)
        self.tag_extractor = TagExtractor(tag_set=tag_set, morpheme_analyzer=morpheme_analyzer)

    def get_tags(self, post_id: int) -> list[str]:
        """
        게시글에 대한 키워드와 태그를 저장 및 반환
        :param post_id: 게시글 id
        :return: 게시글에 달린 태그
        """
        title, post_text, author = self.database_controller.get_data(post_id=post_id)
        tag_list, keyword_list = self.tag_extractor.get_tags(title=title, post_text=post_text, return_keyword=True)
        self.database_controller.save_keywords(post_id=post_id, keyword_list=keyword_list)
        self.database_controller.save_tags(post_id=post_id, tag_list=tag_list)
        return tag_list

    def add_tag(self, tag: str):
        self.database_controller._execute(sql='INSERT INTO tag(name) VALUE (%s)', args=[tag])
        keyword_dict = dict()
        for inner in self.database_controller._execute(
                sql='SELECT keyword_post.post_id, keyword.name FROM (keyword_post left join keyword on keyword_post.keyword_id = keyword.id)'):
            post_id, keyword = inner
            if keyword_dict.get(post_id) is None:
                keyword_dict[post_id] = [keyword]
            else:
                keyword_dict.get(post_id).append(keyword)

        for post_id in keyword_dict.keys():
            if self.tag_extractor.similarity_comparator.is_similar(tag, keyword_dict.get(post_id),
                                                                   point=self.similarity_point):
                self.database_controller.save_tag(post_id=post_id, tag=tag)

        self.tag_extractor._get_tags()

    def tag_all(self, reset_keyword_post_table: bool = False, reset_tag_post_table: bool = False):
        if reset_keyword_post_table:
            self.database_controller._execute('DELETE FROM keyword_post')
        if reset_tag_post_table:
            self.database_controller._execute('DELETE FROM tag_post')
        for inner in self.database_controller._execute('SELECT id FROM post'):
            id = inner[0]
            self.get_tags(post_id=id)
