import re
from bs4 import BeautifulSoup, Comment
from lxml import html
from instructor import from_openai
from pydantic import BaseModel, Field
import openai
from langsmith.trace import traceable  # ✅ Correct import

# Set your project and API key in environment or config
import os
os.environ["LANGCHAIN_API_KEY"] = "<your-langsmith-api-key>"
os.environ["LANGCHAIN_PROJECT"] = "pharma-xpath-validator"

class SelectorSchema(BaseModel):
    title_selector: str = Field(..., description="XPath selector for the title")
    date_selector: str = Field(..., description="XPath selector for the date")
    date_format_pattern: str = Field(..., description="Datetime format string")
    content_selector: str = Field(..., description="XPath selector for the article content")

def clean_html_for_llm(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    return soup.prettify()[:12000]

@traceable(name="Generate XPaths from HTML")
def generate_selectors(cleaned_html: str, api_key: str) -> SelectorSchema:
    client = from_openai(openai.OpenAI(api_key=api_key))
    prompt = f"""You are a scraping expert. Given this cleaned HTML, extract the most accurate XPath selectors for:
1. The main article title
2. The publication date
3. The body/content of the article
Return them in JSON format with `title_selector`, `date_selector`, `date_format_pattern`, and `content_selector` keys.

Cleaned HTML:
{cleaned_html}"""
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_model=SelectorSchema
    )

def extract_values_from_html(html_str: str, selectors: SelectorSchema):
    tree = html.fromstring(html_str)
    def get_text(el): return el.text_content().strip() if el is not None else ""
    try:
        return {
            "title": get_text(tree.xpath(selectors.title_selector)[0]) if tree.xpath(selectors.title_selector) else "❌ Title not found",
            "date": get_text(tree.xpath(selectors.date_selector)[0]) if tree.xpath(selectors.date_selector) else "❌ Date not found",
            "content": " ".join([get_text(p) for p in tree.xpath(selectors.content_selector)])[:2000]
        }
    except Exception as e:
        return {"title": "❌", "date": "❌", "content": f"Error: {str(e)}"}
