# backend/app/services/import_pipeline/adapters/notion.py
"""Notion API v2023-06-01 adapter"""
import httpx
import structlog
from typing import Optional
from dataclasses import dataclass, field

logger = structlog.get_logger()
NOTION_VERSION = "2023-06-01"


@dataclass
class NotionPage:
    id: str
    title: str
    content: str
    url: str
    created_time: str
    tags: list[str] = field(default_factory=list)


async def import_notion_page(page_id: str, token: str) -> Optional[NotionPage]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        # ページ情報取得
        resp = await client.get(f"https://api.notion.com/v1/pages/{page_id}")
        resp.raise_for_status()
        page_data = resp.json()

        # ブロック取得
        blocks_resp = await client.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            params={"page_size": 100},
        )
        blocks_resp.raise_for_status()
        blocks_data = blocks_resp.json()

    title = _extract_title(page_data)
    content = _blocks_to_markdown(blocks_data.get("results", []))
    url = page_data.get("url", "")
    created_time = page_data.get("created_time", "")

    logger.info("notion_imported", page_id=page_id, title=title[:50])
    return NotionPage(id=page_id, title=title, content=content, url=url, created_time=created_time)


def _extract_title(page: dict) -> str:
    props = page.get("properties", {})
    for key in ("Name", "Title", "title"):
        if key in props:
            title_prop = props[key]
            if "title" in title_prop:
                texts = title_prop["title"]
                return "".join(t.get("plain_text", "") for t in texts)
    return "Untitled"


def _blocks_to_markdown(blocks: list[dict]) -> str:
    lines = []
    for block in blocks:
        btype = block.get("type", "")
        content = block.get(btype, {})
        rich_texts = content.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich_texts)

        if btype == "heading_1":
            lines.append(f"# {text}")
        elif btype == "heading_2":
            lines.append(f"## {text}")
        elif btype == "heading_3":
            lines.append(f"### {text}")
        elif btype == "bulleted_list_item":
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"1. {text}")
        elif btype == "code":
            lang = content.get("language", "")
            lines.append(f"```{lang}\n{text}\n```")
        elif btype == "quote":
            lines.append(f"> {text}")
        elif btype == "divider":
            lines.append("---")
        elif text:
            lines.append(text)

    return "\n\n".join(lines)
