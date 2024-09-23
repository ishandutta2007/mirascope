from mirascope.core import anthropic, prompt_template


@anthropic.call("claude-3-5-sonnet-20240620")
@prompt_template()
def recommend_book(genre: str) -> str:
    return f"Recommend a {genre} book"


print(recommend_book("fantasy"))
