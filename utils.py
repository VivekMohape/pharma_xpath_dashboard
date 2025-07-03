import re
from bs4 import BeautifulSoup, Comment
from lxml import html
from pydantic import BaseModel, Field
from instructor import from_openai
from openai import OpenAI
from langsmith import wrappers

class SelectorSchema(BaseModel):
    title_selector: str = Field(..., description="XPath selector for the title")
    date_selector: str = Field(..., description="XPath selector for the date")
    date_format_pattern: str = Field(..., description="Date format")
    content_selector: str = Field(..., description="XPath selector for the article content")

def clean_html_for_llm(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")

    # Remove unwanted tags
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return soup.prettify()[:12000]

def generate_selectors(cleaned_html: str) -> SelectorSchema:
    client = wrappers.wrap_openai(OpenAI())
    client = from_openai(client)

    prompt = f"""
    You are a web scraping expert. Given this cleaned HTML, extract valid XPath selectors for:
    - title_selector
    - date_selector
    - date_format_pattern
    - content_selector
    
    Cleaned HTML:
    {cleaned_html}
    """

    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_model=SelectorSchema
    )

def extract_values_from_html(html_str: str, selectors: SelectorSchema):
    tree = html.fromstring(html_str)

    def get_text(el):
        return el.text_content().strip() if el is not None else ""

    try:
        title = get_text(tree.xpath(selectors.title_selector)[0]) if tree.xpath(selectors.title_selector) else "❌ Title not found"
        date = get_text(tree.xpath(selectors.date_selector)[0]) if tree.xpath(selectors.date_selector) else "❌ Date not found"
        content_elements = tree.xpath(selectors.content_selector)
        content = " ".join([get_text(p) for p in content_elements if get_text(p)])[:2000]
        return {"title": title, "date": date, "content": content}
    except Exception as e:
        return {"title": "❌", "date": "❌", "content": f"Error: {str(e)}"}
