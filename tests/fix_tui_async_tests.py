
with open('tests/test_tui_paper.py', encoding='utf-8') as f:
    content = f.read()

replacement = '''class TestPaperAsync:
    @pytest.mark.asyncio
    async def test_paper_screen_pushes(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            app._show("paper")
            await pilot.pause()
            assert app._content_switcher.current == "view-paper"

    @pytest.mark.asyncio
    async def test_paper_screen_widgets_mounted(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            app._show("paper")
            await pilot.pause()
            screen = app.query_one("#view-paper")
            assert screen.query_one("#session-widget") is not None
            assert screen.query_one("#account-widget") is not None
            assert screen.query_one("#portfolio-widget") is not None
            assert screen.query_one("#performance-widget") is not None
            assert screen.query_one("#position-widget") is not None
            assert screen.query_one("#orders-widget") is not None
            assert screen.query_one("#trades-widget") is not None

    @pytest.mark.asyncio
    async def test_paper_title_shown(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            app._show("paper")
            await pilot.pause()
            screen = app.query_one("#view-paper")
            title = screen.query_one("#paper-title", Static)
            assert "Paper Trading" in str(title.render())

    @pytest.mark.asyncio
    async def test_paper_refresh_indicator(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            app._show("paper")
            await pilot.pause()
            screen = app.query_one("#view-paper")
            indicator = screen.query_one("#refresh-indicator", Static)
            assert indicator is not None

    @pytest.mark.asyncio
    async def test_paper_manual_refresh(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            app._show("paper")
            await pilot.pause()
            screen = app.query_one("#view-paper")
            screen.action_refresh()
            indicator = screen.query_one("#refresh-indicator", Static)
            assert "Last refresh:" in str(indicator.render())

    @pytest.mark.asyncio
    async def test_paper_escape_back(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            app._show("paper")
            await pilot.pause()
            assert app._content_switcher.current == "view-paper"
            await pilot.press("escape")
            assert app._content_switcher.current == "view-dashboard"

    @pytest.mark.asyncio
    async def test_f3_navigates_to_paper(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f3")
            assert app._content_switcher.current == "view-paper"

    @pytest.mark.asyncio
    async def test_f1_navigates_to_dashboard(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            app._show("paper")
            await pilot.pause()
            await pilot.press("f1")
            assert app._content_switcher.current == "view-dashboard"'''

# Find class TestPaperAsync: and replace it and everything after it
idx = content.find('class TestPaperAsync:')
if idx != -1:
    new_content = content[:idx] + replacement + '\n'
    with open('tests/test_tui_paper.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("TestPaperAsync rewritten.")
else:
    print("class TestPaperAsync not found.")
