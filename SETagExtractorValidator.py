from tqdm.auto import tqdm
import numpy as np

from SETagExtractor import DatabaseController
from src.MorphemeAnalyzer import MorphemeAnalyzer
from src.TagExtractor import TagExtractor


class SETagExtractorTest:
    def __init__(self, user: str, password: str, host: str, db: str):
        self.database = DatabaseController(user, password, host, db)

        self.amount_of_tag = float(self.database._execute('SELECT count(tag_id) FROM answer_tag_post')[0][0])
        self.answer_list = dict()
        for tag_id, post_id in self.database._execute(
                'SELECT tag.name as tag, post_id FROM (answer_tag_post right join tag on answer_tag_post.tag_id = tag.id)'):
            if self.answer_list.get(post_id) is None:
                self.answer_list[post_id] = [tag_id]
            else:
                self.answer_list.get(post_id).append(tag_id)

        self.post_list = []
        for id, title, content, author, _ in self.database._execute(
                'SELECT * FROM post WHERE id IN (SELECT post_id FROM answer_tag_post)'):
            self.post_list.append((id, title, content, author))

        self.tag_set = self.database.get_tag_set()
        self.morpheme_analyzer = MorphemeAnalyzer()
        for tag in self.tag_set:
            self.morpheme_analyzer.add_user_word(word=tag)

    def test(self, ngram_range: tuple[int, int] = (1, 3), score_point: float = 0.3,
             similarity_point: float = 0.75) -> list[float, float, float, float, float]:
        sum_of_percent_in_tag_list = .0
        sum_of_percent_in_answer = .0
        tag_extractor = TagExtractor(tag_set=self.tag_set, morpheme_analyzer=self.morpheme_analyzer)
        for id, title, content, author in self.post_list:
            hit_count = 0
            tag_list = tag_extractor.get_tags(title=title, post_text=content, keyword_ngram_range=ngram_range,
                                              score_point=score_point,
                                              similarity_point=similarity_point)
            if len(tag_list) == 0:
                if len(self.answer_list[id]) == 0:
                    sum_of_percent_in_tag_list += 100
            else:
                for tag in tag_list:
                    if tag in self.answer_list[id]:
                        hit_count += 1
                percent_in_tag_list = round(hit_count / len(tag_list) * 100, 3)
                percent_in_answer = round(hit_count / len(self.answer_list[id]) * 100, 3)
                sum_of_percent_in_tag_list += percent_in_tag_list
                sum_of_percent_in_answer += percent_in_answer

                # print(str(id) + ' tag :' + str(tag_list) + ', answer:' + str(self.answer_list[id]) + ', score:' + str(
            #         percent) + '%')

        answer_in_tag_list = sum_of_percent_in_tag_list / len(self.post_list)
        tag_in_answer = sum_of_percent_in_answer / len(self.post_list)
        accuracy = (answer_in_tag_list + tag_in_answer) / 2
        return [ngram_range, score_point, similarity_point, answer_in_tag_list, tag_in_answer, accuracy]


tester = SETagExtractorTest(user='sig', password='sig1234', host='119.63.246.52', db='SIG')
record_list = [['ngram_range', 'score_point', 'similarity_point', 'answer_in_tag_list', 'tag_in_answer', 'accuracy']]

for ngram_range_min in tqdm(range(1, 6), ncols=200, ascii=True, desc='ngram_min'):
    for ngram_range_max in tqdm(range(ngram_range_min, 6), ncols=150, leave=False, ascii=True, desc='ngram_max'):
        ngram_range = (ngram_range_min, ngram_range_max)
        result = tester.test(ngram_range=ngram_range)
        record_list.append(result)

with open('accuracy_test.txt', 'w') as f:
    to_save_list = []
    for inner in record_list:
        line = str(inner)
        to_save = line[1:len(line) - 2]
        print(to_save)
        to_save_list.append(to_save + '\n')
    f.writelines(to_save_list)
    f.close()
