import type { CallReport } from "../app/types";

export function CallReportCard({ report }: { report: CallReport }) {
  return (
    <section className="call-report-card" aria-label="通话报告">
      <div className="call-report-header">
        <strong>{report.sceneTitle} 通话报告</strong>
        <span>
          {report.userName} · {report.startedAt} - {report.endedAt}
        </span>
      </div>
      <p>{report.summary}</p>
      <div className="report-metrics-grid">
        <span>
          <small>时长</small>
          <strong>
            {Math.floor(report.durationSeconds / 60)}m {report.durationSeconds % 60}s
          </strong>
        </span>
        <span>
          <small>轮次</small>
          <strong>
            {report.userTurns}/{report.assistantTurns}
          </strong>
        </span>
        <span>
          <small>Token</small>
          <strong>{report.tokens === null ? "待返回" : report.tokens.toLocaleString("zh-CN")}</strong>
        </span>
        <span>
          <small>首包</small>
          <strong>{report.metrics.firstAudioMs === undefined ? "待记录" : `${report.metrics.firstAudioMs}ms`}</strong>
        </span>
        <span>
          <small>预热</small>
          <strong>{report.metrics.playbackReadyMs === undefined ? "待记录" : `${report.metrics.playbackReadyMs}ms`}</strong>
        </span>
        <span>
          <small>首播排队</small>
          <strong>{report.metrics.firstPlaybackScheduledMs === undefined ? "待记录" : `${report.metrics.firstPlaybackScheduledMs}ms`}</strong>
        </span>
      </div>
    </section>
  );
}
