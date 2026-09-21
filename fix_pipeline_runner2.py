
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            from titan.pipeline.models import PipelineReport
            report = PipelineReport()"""

replacement = """            from titan.pipeline.models import PipelineReport, PipelineStatus
            import uuid
            from datetime import datetime, UTC
            report = PipelineReport(
                pipeline_id=str(uuid.uuid4()),
                symbol=symbol,
                exchange=exchange_val,
                status=PipelineStatus.FAILED,
                stages=(),
                evidence_count=0,
                decision_action=None,
                orders_submitted=0,
                orders_accepted=0,
                orders_rejected=0,
                broker_order_ids=(),
                execution_result=None,
                warnings=(),
                errors=(str(e),),
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                total_duration_ms=0.0
            )"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
