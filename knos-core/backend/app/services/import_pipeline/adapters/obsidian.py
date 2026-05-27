# backend/app/services/import_pipeline/adapters/obsidian.py
"""Obsidianエクスポート Markdown zip インポーター"""
import re
import zipfile
import io
import structlog
from dataclasses import dataclass, field

logger = structlog.get_logger()


@dataclass
class ObsidianNote:
    filename: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)


def import_obsidian_zip(zip_bytes: bytes) -> list[ObsidianNote]:
    """Obsidian zipを解凍して全Markdownをパース"""
    notes = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        md_files = [n for n in zf.namelist() if n.endswith(".md")]
        logger.info("obsidian_zip_opened", total_files=len(md_files))

        for fname in md_files:
            try:
                content = zf.read(fname).decode("utf-8", errors="replace")
                note = _parse_note(fname, content)
                notes.append(note)
            except Exception as e:
                logger.warning("obsidian_note_parse_failed", file=fname, error=str(e))

    logger.info("obsidian_import_completed", notes=len(notes))
    return notes


def _parse_note(filename: str, content: str) -> ObsidianNote:
    title = re.sub(r"\.md$", "", filename.split("/")[-1])
    tags: list[str] = []

    # フロントマターのタグ
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        tag_match = re.search(r"tags:\s*\[([^\]]+)\]", fm)
        if tag_match:
            tags = [t.strip().strip('"\'') for t in tag_match.group(1).split(",")]
        title_match = re.search(r"title:\s*(.+)", fm)
        if title_match:
            title = title_match.group(1).strip().strip('"\'')

    # インラインタグ
    inline_tags = re.findall(r"#([a-zA-Z0-9_/\u3000-\u9fff]+)", content)
    tags.extend(inline_tags)
    tags = list(set(tags))

    # [[wiki-link]] を抽出
    wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)

    # wiki-linkをMarkdownリンクに変換（ベストエフォート）
    content = re.sub(r"\[\[([^\|]+)\|([^\]]+)\]\]", r"[\2](\1)", content)
    content = re.sub(r"\[\[([^\]]+)\]\]", r"[\1](\1)", content)

    return ObsidianNote(
        filename=filename,
        title=title,
        content=content,
        tags=tags,
        wikilinks=wikilinks,
    )


# ─── X (Twitter) Archive ───

@dataclass
class TweetEntry:
    tweet_id: str
    content: str
    created_at: str
    liked_at: str = ""
    author: str = ""


def import_x_archive(json_data: list[dict], mode: str = "liked") -> list[TweetEntry]:
    """Xアーカイブ tweets.js / like.js をパース"""
    entries = []

    for item in json_data:
        tweet = item.get("tweet", item.get("like", item))
        tweet_id = tweet.get("id_str", tweet.get("tweetId", ""))
        full_text = tweet.get("full_text", tweet.get("text", ""))
        created_at = tweet.get("created_at", "")
        liked_at = tweet.get("liked_at", created_at)
        user = tweet.get("user", {})
        author = user.get("screen_name", "") if isinstance(user, dict) else ""

        if not full_text:
            continue

        entries.append(TweetEntry(
            tweet_id=tweet_id,
            content=full_text,
            created_at=created_at,
            liked_at=liked_at,
            author=author,
        ))

    logger.info("x_archive_imported", count=len(entries), mode=mode)
    return entries
