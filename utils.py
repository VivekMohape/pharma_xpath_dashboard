import re
import os
from bs4 import BeautifulSoup, Comment
from lxml import html
from instructor import from_openai
from pydantic import BaseModel, Field
import openai
from langsmith.trace import traceable


# Structured schema for output
class SelectorSchema(BaseModel):
    title_selector: str = Field(..., description="XPath selector for the title")
    date_selector: str = Field(..., description="XPath selector for the publication date")
    date_format_pattern: str = Field(..., description="Datetime format string")
    content_selector: str = Field(..., description="XPath selector for the content")

def configure_langsmith_tracing():
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "pharma_xpath_validator")
    os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")  # Set in .env or system env

# Clean HTML using BeautifulSoup
def clean_html_for_llm(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")

    # Remove noisy tags
    for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return soup.prettify()[:12000]  # LLM context size limit

# Generate selectors with Instructor + LangSmith trace
@traceable(name="Generate XPaths from HTML", project_name="pharma_xpath_validator")
def generate_selectors(cleaned_html: str, api_key: str) -> SelectorSchema:
    client = from_openai(openai.OpenAI(api_key=api_key),tracing=True)

    prompt = f"""You are a scraping expert. Given this cleaned HTML, extract the most accurate XPath selectors for:
1. The main article title
2. The publication date
3. The body/content of the article

Return them in JSON format using these keys:
- `title_selector`
- `date_selector`
- `date_format_pattern`
- `content_selector`

Cleaned HTML:
{cleaned_html}"""

    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_model=SelectorSchema
    )

# Use XPath to extract values
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
