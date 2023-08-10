### model
https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.ko.300.bin.gz

### 사용 방법
```python
import SETagExtractor

se_tag_extractor = SETagExtractor(user='root', password='1234', host='localhost', db='data')
tag_list = se_tag_extractor.get_tags(post_id='1')
```