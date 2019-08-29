def clean_content(content):
    content = content.replace("@everyone", "@\u200beveryone")
    content = content.replace("@here", "@\u200bhere")
    return content
