"""把公开页面的有限元数据转换为可持久化的公开样本快照。"""

from datetime import datetime
from html.parser import HTMLParser

from backend.app.domain.public_snapshot import (
    PublicSnapshot,
    PublicSnapshotError,
    normalize_public_snapshot,
)


class PublicSnapshotHtmlParser(HTMLParser):
    """只读取允许的公开元数据，不保存或返回原始 HTML。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.raw: dict[str, object] = {"attributes": {}, "sample_size": 1}
        self._title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() != "meta":
            return
        key = values.get("property") or values.get("name")
        content = values.get("content", "").strip()
        if not key or not content:
            return
        normalized_key = key.lower()
        mapping = {
            "og:title": "title",
            "og:price:amount": "price_minor",
            "product:price:amount": "price_minor",
            "og:price:currency": "currency",
            "product:price:currency": "currency",
            "ratingvalue": "rating",
            "product:rating": "rating",
            "reviewcount": "review_count",
            "product:review_count": "review_count",
            "og:image": "image_url",
        }
        field = mapping.get(normalized_key)
        if field:
            self.raw[field] = content
        elif normalized_key.startswith("product:attribute:"):
            name = normalized_key.removeprefix("product:attribute:").strip()
            if name:
                attributes = self.raw["attributes"]
                assert isinstance(attributes, dict)
                attributes[name] = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    def build(self, *, url: str, sampled_at: datetime) -> PublicSnapshot:
        if self._title_parts and "title" not in self.raw:
            self.raw["title"] = " ".join("".join(self._title_parts).split())
        if "price_minor" in self.raw:
            try:
                self.raw["price_minor"] = round(float(str(self.raw["price_minor"])) * 100)
            except ValueError as error:
                raise PublicSnapshotError("公开价格无法解析") from error
        self.raw["url"] = url
        return normalize_public_snapshot(self.raw, sampled_at=sampled_at)


def parse_public_snapshot_html(
    *, url: str, html: str, sampled_at: datetime
) -> PublicSnapshot:
    """解析有限公开字段；解析失败时返回可操作的业务错误，不暴露原文。"""
    parser = PublicSnapshotHtmlParser()
    parser.feed(html)
    return parser.build(url=url, sampled_at=sampled_at)
