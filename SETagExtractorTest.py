from SETagExtractor import SETagExtractor

SETagExtractor(user='sig', password='sig1234', host='119.63.246.52', db='SIG').tag_all(reset_tag_post_table=True,
                                                                                       reset_keyword_post_table=True)
