from bs4 import BeautifulSoup
from lxml import html
from instructor import from_openai
from pydantic import BaseModel, Field
import openai

class SelectorSchema(BaseModel):
    title_selector: str = Field(...)
    date_selector: str = Field(...)
    date_format_pattern: str = Field(...)
    content_selector: str = Field(...)

def clean_html_for_llm(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()
    return str(soup)[:12000]

def generate_selectors(cleaned_html, api_key: str):
    client = from_openai(openai.OpenAI(api_key=api_key))
    prompt = f"""You are a scraping expert. Return valid XPath selectors for title, date, and content from this HTML:\n\n{cleaned_html}"""
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_model=SelectorSchema
    )

def extract_values_from_html(html_str, selectors):
    tree = html.fromstring(html_str)
    def get_text(e): return e.text_content().strip() if e is not None else ""
    try:
        return {
            "title": get_text(tree.xpath(selectors.title_selector)[0]) if tree.xpath(selectors.title_selector) else "❌ Title not found",
            "date": get_text(tree.xpath(selectors.date_selector)[0]) if tree.xpath(selectors.date_selector) else "❌ Date not found",
            "content": " ".join([get_text(p) for p in tree.xpath(selectors.content_selector)])[:1000]
        }
    except Exception as e:
        return {"title": "❌", "date": "❌", "content": str(e)}
