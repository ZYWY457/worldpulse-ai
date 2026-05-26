from typing import Any


class IngestionPipeline:
    def __init__(self, rss_collector, gdelt_collector, static_page_collector, task_control):
        self.rss_collector = rss_collector
        self.gdelt_collector = gdelt_collector
        self.static_page_collector = static_page_collector
        self.task_control = task_control

    def run(self) -> dict[str, Any]:
        self.task_control.reset()
        rss_count = self.rss_collector.collect()
        if self.task_control.is_cancelled():
            return {"ok": False, "message": f"采集已取消。RSS: {rss_count}.", "count": rss_count}

        gdelt_count = self.gdelt_collector.collect()
        if self.task_control.is_cancelled():
            return {
                "ok": False,
                "message": f"采集已取消。RSS: {rss_count}, GDELT: {gdelt_count}.",
                "count": rss_count + gdelt_count,
            }

        crawler_count = self.static_page_collector.collect()
        total_count = rss_count + gdelt_count + crawler_count
        if self.task_control.is_cancelled():
            return {
                "ok": False,
                "message": f"采集已取消。RSS: {rss_count}, GDELT: {gdelt_count}, 轻爬虫: {crawler_count}.",
                "count": total_count,
            }

        return {
            "ok": True,
            "message": f"采集完成并已写入缓存库。RSS: {rss_count}, GDELT: {gdelt_count}, 轻爬虫: {crawler_count}.",
            "count": total_count,
        }


class ProcessingPipeline:
    def __init__(self, rule_geotagger, aggregator, task_control, *, geotag_limit: int = 200, repair_limit: int = 500):
        self.rule_geotagger = rule_geotagger
        self.aggregator = aggregator
        self.task_control = task_control
        self.geotag_limit = geotag_limit
        self.repair_limit = repair_limit

    def run(self) -> dict[str, Any]:
        self.task_control.reset()
        mapped_count = self.rule_geotagger.geotag_unmapped(limit=self.geotag_limit)
        repaired_count = self.rule_geotagger.repair_existing_locations(limit=self.repair_limit)
        if self.task_control.is_cancelled():
            return {
                "ok": False,
                "message": f"处理已取消。新增定位: {mapped_count}, 修复: {repaired_count}.",
                "count": mapped_count + repaired_count,
            }

        cluster_count = self.aggregator.rebuild_recent_clusters(hours=168)
        return {
            "ok": True,
            "message": f"处理完成。新增定位: {mapped_count}, 修复: {repaired_count}, 事件簇: {cluster_count}.",
            "count": mapped_count + repaired_count,
        }
