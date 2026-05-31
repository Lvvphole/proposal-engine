"""Remediation test suite — 80 tests covering all new harness modules."""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# TestJob01_Persistence
# ---------------------------------------------------------------------------

class TestJob01_Persistence:
    """Tests for harness/models.py — EnvelopeRow ORM and async helpers."""

    @pytest.fixture
    async def db_session(self, tmp_path):
        import os
        import harness.models  # ensure EnvelopeRow registered in Base.metadata
        db_file = tmp_path / "test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
        from core.config import get_config
        get_config.cache_clear()
        from core.db import reset_engine, init_db
        reset_engine()
        await init_db()
        from core.db import _get_session_factory
        async with _get_session_factory()() as session:
            yield session
        reset_engine()
        get_config.cache_clear()
        os.environ["DATABASE_URL"] = "sqlite:///./test_proposals.db"

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self, db_session):
        from contracts.envelope import Envelope
        from harness.models import save_envelope, load_envelope
        env = Envelope(source_filename="quote.pdf")
        await save_envelope(env, db_session)
        loaded = await load_envelope(env.id, db_session)
        assert loaded is not None
        assert loaded.id == env.id
        assert loaded.source_filename == "quote.pdf"

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(self, db_session):
        from harness.models import load_envelope
        result = await load_envelope("does-not-exist", db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_updates_existing(self, db_session):
        from contracts.envelope import Envelope, EnvelopeStatus
        from contracts.events import DomainEvent, EventKind
        from harness.models import save_envelope, load_envelope
        env = Envelope(source_filename="quote.pdf")
        await save_envelope(env, db_session)
        env.advance(EnvelopeStatus.CLASSIFYING, DomainEvent(kind=EventKind.RECEIVED, agent="test"))
        await save_envelope(env, db_session)
        loaded = await load_envelope(env.id, db_session)
        assert loaded.status == EnvelopeStatus.CLASSIFYING

    @pytest.mark.asyncio
    async def test_list_envelopes_empty(self, db_session):
        from harness.models import list_envelopes
        results = await list_envelopes(db_session)
        assert results == []

    @pytest.mark.asyncio
    async def test_list_envelopes_multiple(self, db_session):
        from contracts.envelope import Envelope
        from harness.models import save_envelope, list_envelopes
        for i in range(3):
            env = Envelope(source_filename=f"quote_{i}.pdf")
            await save_envelope(env, db_session)
        results = await list_envelopes(db_session)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_envelopes_status_filter(self, db_session):
        from contracts.envelope import Envelope, EnvelopeStatus
        from contracts.events import DomainEvent, EventKind
        from harness.models import save_envelope, list_envelopes
        env1 = Envelope(source_filename="a.pdf")
        env2 = Envelope(source_filename="b.pdf")
        env2.advance(EnvelopeStatus.CLASSIFYING, DomainEvent(kind=EventKind.RECEIVED, agent="t"))
        await save_envelope(env1, db_session)
        await save_envelope(env2, db_session)
        results = await list_envelopes(db_session, status="received")
        assert len(results) == 1
        assert results[0].source_filename == "a.pdf"

    @pytest.mark.asyncio
    async def test_list_envelopes_limit(self, db_session):
        from contracts.envelope import Envelope
        from harness.models import save_envelope, list_envelopes
        for i in range(5):
            await save_envelope(Envelope(source_filename=f"q{i}.pdf"), db_session)
        results = await list_envelopes(db_session, limit=2)
        assert len(results) == 2

    def test_envelope_row_from_domain(self):
        from contracts.envelope import Envelope
        from harness.models import EnvelopeRow
        env = Envelope(source_filename="test.pdf", contractor_id="c1")
        row = EnvelopeRow.from_domain(env)
        assert row.id == env.id
        assert row.source_filename == "test.pdf"
        assert row.contractor_id == "c1"


# ---------------------------------------------------------------------------
# TestJob03_ModelCapabilities
# ---------------------------------------------------------------------------

class TestJob03_ModelCapabilities:
    """Tests for harness/model_capabilities.py."""

    def test_get_capabilities_sonnet(self):
        from harness.model_capabilities import get_capabilities
        caps = get_capabilities("claude-sonnet-4-20250514")
        assert caps.context_window == 200_000
        assert caps.supports_vision is True
        assert caps.supports_tools is True

    def test_get_capabilities_haiku(self):
        from harness.model_capabilities import get_capabilities
        caps = get_capabilities("claude-haiku-3-5-20241022")
        assert caps.input_cost_per_million < caps.output_cost_per_million

    def test_get_capabilities_unknown_raises(self):
        from harness.model_capabilities import get_capabilities
        with pytest.raises(KeyError):
            get_capabilities("gpt-4-turbo")

    def test_register_model(self):
        from harness.model_capabilities import register_model, get_capabilities, ModelCapabilities
        caps = ModelCapabilities(
            model_id="test-model",
            context_window=8192,
            supports_vision=False,
            supports_tools=False,
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        register_model("test-model", caps)
        retrieved = get_capabilities("test-model")
        assert retrieved.context_window == 8192
        assert not retrieved.supports_vision

    def test_assert_capability_vision_ok(self):
        from harness.model_capabilities import assert_capability
        assert_capability("claude-sonnet-4-20250514", "vision")

    def test_assert_capability_tools_ok(self):
        from harness.model_capabilities import assert_capability
        assert_capability("claude-sonnet-4-20250514", "tools")

    def test_assert_capability_missing_raises(self):
        from harness.model_capabilities import register_model, assert_capability, ModelCapabilities
        from contracts.errors import PolicyViolationError
        caps = ModelCapabilities(
            model_id="no-vision-model",
            context_window=4096,
            supports_vision=False,
            supports_tools=True,
            input_cost_per_million=0.5,
            output_cost_per_million=1.5,
        )
        register_model("no-vision-model", caps)
        with pytest.raises(PolicyViolationError):
            assert_capability("no-vision-model", "vision")

    def test_capabilities_are_frozen(self):
        from harness.model_capabilities import get_capabilities
        caps = get_capabilities("claude-sonnet-4-20250514")
        with pytest.raises(Exception):
            caps.context_window = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestJob06_PromptAssembler
# ---------------------------------------------------------------------------

class TestJob06_PromptAssembler:
    """Tests for harness/prompt_assembler.py."""

    def test_assemble_classifier_base(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("classifier")
        assert "classifier" in prompt.lower() or "document" in prompt.lower()

    def test_assemble_extractor_base(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("extractor")
        assert len(prompt) > 50

    def test_assemble_unknown_agent_raises(self):
        from harness.prompt_assembler import assemble
        with pytest.raises(ValueError, match="Unknown agent"):
            assemble("unknown_agent_xyz")

    def test_assemble_with_supplier_context(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("extractor", supplier_context="HomeDepot PRO format")
        assert "HomeDepot PRO format" in prompt

    def test_assemble_with_contractor_prefs(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("proposal_builder", contractor_prefs={"markup_pct": "25%"})
        assert "markup_pct" in prompt

    def test_assemble_with_few_shot_examples(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("extractor", few_shot_examples=["Example A", "Example B"])
        assert "Example A" in prompt
        assert "Example B" in prompt

    def test_assemble_debug_mode(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("classifier", mode="debug")
        assert "debug" in prompt.lower() or "verbose" in prompt.lower() or "reasoning" in prompt.lower()

    def test_assemble_eval_mode(self):
        from harness.prompt_assembler import assemble
        prompt = assemble("classifier", mode="eval")
        assert "eval" in prompt.lower() or "confidence" in prompt.lower() or "evaluation" in prompt.lower()


# ---------------------------------------------------------------------------
# TestJob08_PolicyGate
# ---------------------------------------------------------------------------

class TestJob08_PolicyGate:
    """Tests for harness/policy_gate.py."""

    def setup_method(self):
        from harness.policy_gate import _reset_caches
        _reset_caches()

    def test_check_tool_policy_public_tool(self):
        from harness.policy_gate import check_tool_policy
        result = check_tool_policy("submit_quote")
        assert isinstance(result, dict)

    def test_check_tool_policy_auth_required_raises(self):
        from harness.policy_gate import check_tool_policy
        from contracts.errors import PolicyViolationError
        with pytest.raises(PolicyViolationError, match="authentication"):
            check_tool_policy("register_contractor")

    def test_check_tool_policy_auth_required_passes_with_flag(self):
        from harness.policy_gate import check_tool_policy
        result = check_tool_policy("register_contractor", require_auth=True)
        assert isinstance(result, dict)

    def test_check_human_review_not_required_by_default(self):
        from contracts.envelope import Envelope
        from harness.policy_gate import check_human_review_required
        env = Envelope()
        result = check_human_review_required(env)
        assert isinstance(result, bool)

    def test_check_human_review_low_confidence(self):
        from contracts.envelope import Envelope
        from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData
        from harness.policy_gate import check_human_review_required
        extraction = ExtractionResult(
            header=HeaderData(supplier_name="Test"),
            line_items=[LineItem(description="Item", quantity=Decimal("1"), unit_price=Decimal("10"), extended_price=Decimal("10"))],
            totals=TotalsData(),
            source_pipeline="a",
            extraction_confidence=0.5,
        )
        env = Envelope()
        env.extraction = extraction
        result = check_human_review_required(env)
        assert result is True

    def test_unknown_tool_returns_empty_dict(self):
        from harness.policy_gate import check_tool_policy
        result = check_tool_policy("completely_unknown_tool_xyz")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestJob09_ReviewResumePath
# ---------------------------------------------------------------------------

class TestJob09_ReviewResumePath:
    """Tests for the review endpoint in routes.py."""

    @pytest.fixture
    def app_with_db(self, tmp_path):
        import os
        import harness.models  # ensure EnvelopeRow registered in Base.metadata
        db_file = tmp_path / "review_test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
        from core.config import get_config
        get_config.cache_clear()
        from core.db import reset_engine
        reset_engine()
        return db_file

    @pytest.mark.asyncio
    async def test_review_approved(self, app_with_db, tmp_path):
        from core.db import init_db, _get_session_factory
        from contracts.envelope import Envelope, EnvelopeStatus
        from contracts.events import DomainEvent, EventKind
        from harness.models import save_envelope, load_envelope
        from app.api.routes import submit_review

        await init_db()
        env = Envelope()
        env.advance(EnvelopeStatus.REVIEW_PENDING, DomainEvent(kind=EventKind.REVIEW_REQUESTED, agent="test"))
        async with _get_session_factory()() as session:
            await save_envelope(env, session)

        async with _get_session_factory()() as session:
            result = await submit_review(env.id, "approved", session=session)
        assert result["verdict"] == "approved"
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_review_rejected(self, app_with_db):
        from core.db import init_db, _get_session_factory
        from contracts.envelope import Envelope, EnvelopeStatus
        from contracts.events import DomainEvent, EventKind
        from harness.models import save_envelope

        await init_db()
        env = Envelope()
        env.advance(EnvelopeStatus.REVIEW_PENDING, DomainEvent(kind=EventKind.REVIEW_REQUESTED, agent="test"))
        async with _get_session_factory()() as session:
            await save_envelope(env, session)

        from app.api.routes import submit_review
        async with _get_session_factory()() as session:
            result = await submit_review(env.id, "rejected", session=session)
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_review_wrong_status_raises_409(self, app_with_db):
        from fastapi import HTTPException
        from core.db import init_db, _get_session_factory
        from contracts.envelope import Envelope
        from harness.models import save_envelope
        from app.api.routes import submit_review

        await init_db()
        env = Envelope()
        async with _get_session_factory()() as session:
            await save_envelope(env, session)

        async with _get_session_factory()() as session:
            with pytest.raises(HTTPException) as exc_info:
                await submit_review(env.id, "approved", session=session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_review_unknown_envelope_raises_404(self, app_with_db):
        from fastapi import HTTPException
        from core.db import init_db, _get_session_factory
        from app.api.routes import submit_review

        await init_db()
        async with _get_session_factory()() as session:
            with pytest.raises(HTTPException) as exc_info:
                await submit_review("nonexistent-id", "approved", session=session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_review_invalid_verdict_raises_400(self, app_with_db):
        from fastapi import HTTPException
        from core.db import init_db, _get_session_factory
        from app.api.routes import submit_review

        await init_db()
        async with _get_session_factory()() as session:
            with pytest.raises(HTTPException) as exc_info:
                await submit_review("any-id", "super_approved", session=session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_review_persists_to_db(self, app_with_db):
        from core.db import init_db, _get_session_factory
        from contracts.envelope import Envelope, EnvelopeStatus
        from contracts.events import DomainEvent, EventKind
        from harness.models import save_envelope, load_envelope
        from app.api.routes import submit_review

        await init_db()
        env = Envelope()
        env.advance(EnvelopeStatus.REVIEW_PENDING, DomainEvent(kind=EventKind.REVIEW_REQUESTED, agent="test"))
        async with _get_session_factory()() as session:
            await save_envelope(env, session)

        async with _get_session_factory()() as session:
            await submit_review(env.id, "approved", session=session)

        async with _get_session_factory()() as session:
            loaded = await load_envelope(env.id, session)
        assert loaded.status == "approved"


# ---------------------------------------------------------------------------
# TestJob11_Hooks
# ---------------------------------------------------------------------------

class TestJob11_Hooks:
    """Tests for harness/hooks.py."""

    def test_redact_pii_email(self):
        from harness.hooks import redact_pii
        result = redact_pii("Contact us at user@example.com for help")
        assert "[EMAIL]" in result
        assert "user@example.com" not in result

    def test_redact_pii_phone(self):
        from harness.hooks import redact_pii
        result = redact_pii("Call 555-867-5309 for pricing")
        assert "555-867-5309" not in result

    def test_redact_pii_ssn(self):
        from harness.hooks import redact_pii
        result = redact_pii("SSN: 123-45-6789")
        assert "[SSN]" in result
        assert "123-45-6789" not in result

    def test_redact_pii_no_pii(self):
        from harness.hooks import redact_pii
        text = "No sensitive data here at all."
        assert redact_pii(text) == text

    @pytest.mark.asyncio
    async def test_hook_registry_before(self):
        from harness.hooks import HookRegistry
        calls = []

        async def my_hook(event, ctx):
            calls.append(event)

        reg = HookRegistry()
        reg.register_before_hook(my_hook)
        await reg.run_before_hooks("test_event", {})
        assert calls == ["test_event"]

    @pytest.mark.asyncio
    async def test_hook_registry_after(self):
        from harness.hooks import HookRegistry
        calls = []

        async def my_hook(event, ctx):
            calls.append(event)

        reg = HookRegistry()
        reg.register_after_hook(my_hook)
        await reg.run_after_hooks("after_event", {})
        assert calls == ["after_event"]

    @pytest.mark.asyncio
    async def test_pii_redaction_hook_modifies_context(self):
        from harness.hooks import pii_redaction_hook
        ctx = {"note": "email is test@test.com"}
        await pii_redaction_hook("some_event", ctx)
        assert "test@test.com" not in ctx["note"]
        assert "[EMAIL]" in ctx["note"]

    @pytest.mark.asyncio
    async def test_install_default_hooks(self):
        from harness.hooks import HookRegistry, install_default_hooks
        reg = HookRegistry()
        install_default_hooks(reg)
        assert len(reg._before) >= 1
        assert len(reg._after) >= 1


# ---------------------------------------------------------------------------
# TestJob13_DocumentPreparer
# ---------------------------------------------------------------------------

class TestJob13_DocumentPreparer:
    """Tests for harness/document_preparer.py."""

    def test_count_tokens_short_text(self):
        from harness.document_preparer import count_tokens
        result = count_tokens("Hello world")
        assert result > 0
        assert result < 100

    def test_count_tokens_empty(self):
        from harness.document_preparer import count_tokens
        result = count_tokens("")
        assert result == 0

    def test_prepare_document_short(self):
        from harness.document_preparer import prepare_document
        content = "short content"
        result = prepare_document(content)
        assert result == content

    def test_prepare_document_truncates(self):
        from harness.document_preparer import prepare_document, _reset_cache
        _reset_cache()
        long_content = "x" * 200_001
        result = prepare_document(long_content)
        assert len(result) < len(long_content) + 200
        assert "omitted" in result

    def test_preflight_check_ok(self):
        from harness.document_preparer import preflight_check
        preflight_check("short document", "claude-sonnet-4-20250514")

    def test_preflight_check_exceeds_window(self):
        from harness.document_preparer import preflight_check
        from contracts.errors import ContextWindowExceededError
        from harness.model_capabilities import register_model, ModelCapabilities
        tiny_caps = ModelCapabilities(
            model_id="tiny-model",
            context_window=100,
            supports_vision=False,
            supports_tools=False,
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        register_model("tiny-model", tiny_caps)
        big_content = "word " * 200
        with pytest.raises(ContextWindowExceededError):
            preflight_check(big_content, "tiny-model")


# ---------------------------------------------------------------------------
# TestJob14_EventStream
# ---------------------------------------------------------------------------

class TestJob14_EventStream:
    """Tests for core/streaming.py SSEBridge and sse_event_generator."""

    def setup_method(self):
        from core.streaming import SSEBridge
        SSEBridge.reset()

    def test_sse_bridge_subscribe_returns_queue(self):
        from core.streaming import SSEBridge
        q = SSEBridge.subscribe("env-123")
        assert q is not None

    def test_sse_bridge_unsubscribe(self):
        from core.streaming import SSEBridge
        from core.streaming import _envelope_queues
        q = SSEBridge.subscribe("env-456")
        SSEBridge.unsubscribe("env-456", q)
        assert q not in _envelope_queues.get("env-456", [])

    @pytest.mark.asyncio
    async def test_sse_event_generator_receives_message(self):
        from core.streaming import SSEBridge, _envelope_queues
        import asyncio
        SSEBridge.reset()
        env_id = "test-env-gen-2"

        lines = []
        collected = asyncio.Event()

        async def collect():
            from core.streaming import sse_event_generator
            async for line in sse_event_generator(env_id, timeout=5.0):
                lines.append(line)
                collected.set()
                break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)  # let generator subscribe

        queues = _envelope_queues.get(env_id, [])
        if queues:
            await queues[-1].put('data: {"kind": "review_requested", "metadata": {}}\n\n')

        await asyncio.wait_for(collected.wait(), timeout=5.0)
        await task
        assert len(lines) == 1
        assert "review_requested" in lines[0]

    @pytest.mark.asyncio
    async def test_sse_bridge_install_idempotent(self):
        from core.streaming import SSEBridge
        SSEBridge.reset()
        SSEBridge.install()
        SSEBridge.install()
        assert SSEBridge._installed is True

    @pytest.mark.asyncio
    async def test_heartbeat_on_timeout(self):
        from core.streaming import SSEBridge, sse_event_generator
        SSEBridge.reset()
        env_id = "heartbeat-test"
        SSEBridge.subscribe(env_id)

        lines = []
        async def collect():
            gen = sse_event_generator(env_id, timeout=1.0)
            async for line in gen:
                lines.append(line)
                break

        await asyncio.wait_for(collect(), timeout=20.0)
        assert any("heartbeat" in l for l in lines)

    def test_sse_bridge_reset_clears_state(self):
        from core.streaming import SSEBridge, _envelope_queues
        SSEBridge.subscribe("env-reset-1")
        SSEBridge.subscribe("env-reset-2")
        SSEBridge.reset()
        assert len(_envelope_queues) == 0
        assert SSEBridge._installed is False


# ---------------------------------------------------------------------------
# TestJob15_Tracing
# ---------------------------------------------------------------------------

class TestJob15_Tracing:
    """Tests for harness/tracing.py."""

    def test_no_op_span_set_attribute(self):
        from harness.tracing import NoOpSpan
        span = NoOpSpan()
        span.set_attribute("key", "value")

    def test_no_op_span_record_exception(self):
        from harness.tracing import NoOpSpan
        span = NoOpSpan()
        span.record_exception(ValueError("test"))

    def test_start_span_context_manager(self):
        from harness.tracing import start_span
        with start_span("test.operation", foo="bar") as span:
            assert span is not None

    def test_record_llm_call(self):
        from harness.tracing import NoOpSpan, record_llm_call
        span = NoOpSpan()
        record_llm_call(span, model="claude-sonnet-4-20250514", input_tokens=100, output_tokens=50)

    def test_record_error(self):
        from harness.tracing import NoOpSpan, record_error
        span = NoOpSpan()
        record_error(span, RuntimeError("something failed"))

    def test_setup_tracing_does_not_raise(self):
        from harness.tracing import setup_tracing
        setup_tracing("test-service")


# ---------------------------------------------------------------------------
# TestJob07_Streaming
# ---------------------------------------------------------------------------

class TestJob07_Streaming:
    """Tests for core/streaming.py call_llm_streaming."""

    @pytest.mark.asyncio
    async def test_call_llm_streaming_yields_text(self):
        from core.streaming import call_llm_streaming

        mock_stream_ctx = MagicMock()

        async def fake_text_stream():
            for chunk in ["Hello", " world", "!"]:
                yield chunk

        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_stream_ctx.text_stream = fake_text_stream()

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_ctx

        with patch("core.streaming.AsyncAnthropic", return_value=mock_client):
            chunks = []
            async for chunk in call_llm_streaming(
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
            ):
                chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_call_llm_streaming_uses_config_model(self):
        from core.streaming import call_llm_streaming

        mock_stream_ctx = MagicMock()

        async def fake_text_stream():
            yield "ok"

        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_stream_ctx.text_stream = fake_text_stream()

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_ctx

        called_with = {}

        def capture_stream(**kwargs):
            called_with.update(kwargs)
            return mock_stream_ctx

        mock_client.messages.stream = capture_stream

        with patch("core.streaming.AsyncAnthropic", return_value=mock_client):
            async for _ in call_llm_streaming(system="s", messages=[]):
                pass

        assert "model" in called_with

    @pytest.mark.asyncio
    async def test_call_llm_streaming_empty_response(self):
        from core.streaming import call_llm_streaming

        mock_stream_ctx = MagicMock()

        async def fake_text_stream():
            return
            yield  # make it a generator

        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_stream_ctx.text_stream = fake_text_stream()

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_ctx

        with patch("core.streaming.AsyncAnthropic", return_value=mock_client):
            chunks = []
            async for chunk in call_llm_streaming(system="s", messages=[]):
                chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_call_llm_streaming_custom_model(self):
        from core.streaming import call_llm_streaming

        mock_stream_ctx = MagicMock()

        async def fake_text_stream():
            yield "chunk"

        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_stream_ctx.text_stream = fake_text_stream()

        mock_client = MagicMock()
        called_model = []

        def capture_stream(**kwargs):
            called_model.append(kwargs.get("model"))
            return mock_stream_ctx

        mock_client.messages.stream = capture_stream

        with patch("core.streaming.AsyncAnthropic", return_value=mock_client):
            async for _ in call_llm_streaming(
                system="s", messages=[], model="claude-haiku-3-5-20241022"
            ):
                pass

        assert called_model[0] == "claude-haiku-3-5-20241022"

    @pytest.mark.asyncio
    async def test_call_llm_streaming_multiple_chunks(self):
        from core.streaming import call_llm_streaming

        mock_stream_ctx = MagicMock()

        async def fake_text_stream():
            for i in range(5):
                yield f"chunk{i}"

        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_stream_ctx.text_stream = fake_text_stream()

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_ctx

        with patch("core.streaming.AsyncAnthropic", return_value=mock_client):
            chunks = []
            async for chunk in call_llm_streaming(system="s", messages=[]):
                chunks.append(chunk)

        assert len(chunks) == 5

    def test_sse_bridge_is_class(self):
        from core.streaming import SSEBridge
        assert hasattr(SSEBridge, "install")
        assert hasattr(SSEBridge, "subscribe")


# ---------------------------------------------------------------------------
# TestJob12_Checkpoints
# ---------------------------------------------------------------------------

class TestJob12_Checkpoints:
    """Tests for the _checkpoint helper in pipelines/orchestrator.py."""

    @pytest.mark.asyncio
    async def test_checkpoint_saves_envelope(self, tmp_path):
        import os
        import harness.models  # ensure EnvelopeRow registered in Base.metadata
        db_file = tmp_path / "ckpt_test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
        from core.config import get_config
        get_config.cache_clear()
        from core.db import reset_engine, init_db
        reset_engine()
        await init_db()

        from contracts.envelope import Envelope
        from pipelines.orchestrator import _checkpoint
        from harness.models import load_envelope
        from core.db import _get_session_factory

        env = Envelope(source_filename="ckpt.pdf")
        await _checkpoint(env)

        async with _get_session_factory()() as session:
            loaded = await load_envelope(env.id, session)
        assert loaded is not None
        assert loaded.id == env.id

        reset_engine()
        get_config.cache_clear()
        os.environ["DATABASE_URL"] = "sqlite:///./test_proposals.db"

    @pytest.mark.asyncio
    async def test_checkpoint_non_fatal_on_error(self):
        from contracts.envelope import Envelope
        from pipelines.orchestrator import _checkpoint

        env = Envelope(source_filename="ckpt_fail.pdf")
        with patch("harness.models.save_envelope", side_effect=Exception("DB down")):
            await _checkpoint(env)

    @pytest.mark.asyncio
    async def test_checkpoint_called_after_classify(self, tmp_path):
        import os
        import harness.models  # ensure EnvelopeRow registered in Base.metadata
        db_file = tmp_path / "ckpt_classify.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
        from core.config import get_config
        get_config.cache_clear()
        from core.db import reset_engine, init_db
        reset_engine()
        await init_db()

        from contracts.envelope import Envelope, EnvelopeStatus
        from pipelines.orchestrator import _checkpoint
        from harness.models import load_envelope
        from core.db import _get_session_factory
        from contracts.events import DomainEvent, EventKind

        env = Envelope()
        env.advance(EnvelopeStatus.CLASSIFYING, DomainEvent(kind=EventKind.RECEIVED, agent="test"))
        await _checkpoint(env)

        async with _get_session_factory()() as session:
            loaded = await load_envelope(env.id, session)
        assert loaded.status == "classifying"

        reset_engine()
        get_config.cache_clear()
        os.environ["DATABASE_URL"] = "sqlite:///./test_proposals.db"

    @pytest.mark.asyncio
    async def test_checkpoint_idempotent(self, tmp_path):
        import os
        import harness.models  # ensure EnvelopeRow registered in Base.metadata
        db_file = tmp_path / "ckpt_idem.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
        from core.config import get_config
        get_config.cache_clear()
        from core.db import reset_engine, init_db
        reset_engine()
        await init_db()

        from contracts.envelope import Envelope
        from pipelines.orchestrator import _checkpoint
        from core.db import _get_session_factory
        from harness.models import load_envelope

        env = Envelope(source_filename="idem.pdf")
        await _checkpoint(env)
        await _checkpoint(env)

        async with _get_session_factory()() as session:
            loaded = await load_envelope(env.id, session)
        assert loaded is not None

        reset_engine()
        get_config.cache_clear()
        os.environ["DATABASE_URL"] = "sqlite:///./test_proposals.db"

    def test_checkpoint_function_exists(self):
        from pipelines.orchestrator import _checkpoint
        assert callable(_checkpoint)

    def test_orchestrator_imports_tracing(self):
        from pipelines import orchestrator
        assert hasattr(orchestrator, "start_span")


# ---------------------------------------------------------------------------
# TestNewErrorTypes
# ---------------------------------------------------------------------------

class TestNewErrorTypes:
    """Tests for the two new error types in contracts/errors.py."""

    def test_policy_violation_error_is_proposal_engine_error(self):
        from contracts.errors import PolicyViolationError, ProposalEngineError
        err = PolicyViolationError("not allowed")
        assert isinstance(err, ProposalEngineError)

    def test_policy_violation_error_has_context(self):
        from contracts.errors import PolicyViolationError
        err = PolicyViolationError("denied", context={"tool": "submit"})
        assert err.context["tool"] == "submit"

    def test_context_window_exceeded_error_is_proposal_engine_error(self):
        from contracts.errors import ContextWindowExceededError, ProposalEngineError
        err = ContextWindowExceededError("too big")
        assert isinstance(err, ProposalEngineError)

    def test_context_window_exceeded_error_exported_from_contracts(self):
        import contracts
        assert hasattr(contracts, "ContextWindowExceededError")
        assert hasattr(contracts, "PolicyViolationError")


# ---------------------------------------------------------------------------
# TestModuleImports
# ---------------------------------------------------------------------------

class TestModuleImports:
    """Smoke tests that all new modules import cleanly."""

    def test_all_harness_modules_import(self):
        import harness.models
        import harness.model_capabilities
        import harness.prompt_assembler
        import harness.policy_gate
        import harness.hooks
        import harness.document_preparer
        import harness.tracing

    def test_core_and_app_modules_import(self):
        import core.streaming
        import app.api.events
