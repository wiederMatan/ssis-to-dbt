#!/usr/bin/env python3
"""
SSIS-to-dbt Migration Factory - Manim Explainer Video

Usage:
    manim -pqh docs/manim_explainer.py SSIStoDBTExplainer

Flags:
    -p  Preview after rendering
    -q  Quality: l=480p, m=720p, h=1080p, k=4K
    -h  High quality (1080p)

Requirements:
    pip install manim
"""

from manim import *
import numpy as np

# =============================================================================
# THEME CONFIGURATION - Developer Dark
# =============================================================================
BACKGROUND_COLOR = "#121212"
PRIMARY_COLOR = "#58a6ff"      # GitHub blue
SECONDARY_COLOR = "#238636"    # Green for success
ACCENT_COLOR = "#f78166"       # Orange/red for warnings
TEXT_COLOR = "#e6edf3"         # Light text
DIM_TEXT_COLOR = "#7d8590"     # Dimmed text
TERMINAL_BG = "#161b22"        # Terminal background
CODE_BG = "#0d1117"            # Code block background

# Custom colors for architecture
SSIS_COLOR = "#e34c26"         # SSIS Orange
DBT_COLOR = "#ff694b"          # dbt Orange
PYTHON_COLOR = "#3572A5"       # Python Blue
SQL_COLOR = "#e38c00"          # SQL Yellow


class SSIStoDBTExplainer(Scene):
    """Main explainer video scene for SSIS-to-dbt Migration Factory."""

    def construct(self):
        """Build the complete animation sequence."""
        self.camera.background_color = BACKGROUND_COLOR

        # Scene 1: Intro with Logo
        self.play_intro()

        # Scene 2: The Problem
        self.play_problem_statement()

        # Scene 3: Architecture Overview
        self.play_architecture()

        # Scene 4: Code Walkthrough
        self.play_code_highlight()

        # Scene 5: Terminal Demo
        self.play_terminal_demo()

        # Scene 6: Results Dashboard
        self.play_results()

        # Scene 7: Outro
        self.play_outro()

    # =========================================================================
    # SCENE 1: INTRO WITH LOGO
    # =========================================================================
    def play_intro(self):
        """Animated intro with project logo and name."""
        # Create SSIS icon (data flow representation)
        ssis_icon = VGroup()
        # Database cylinder
        db_top = Ellipse(width=1, height=0.3, color=SSIS_COLOR, fill_opacity=0.8)
        db_body = Rectangle(width=1, height=0.8, color=SSIS_COLOR, fill_opacity=0.8)
        db_bottom = Ellipse(width=1, height=0.3, color=SSIS_COLOR, fill_opacity=0.8)
        db_body.next_to(db_top, DOWN, buff=0)
        db_bottom.next_to(db_body, DOWN, buff=0)
        db_bottom.shift(UP * 0.15)
        ssis_db = VGroup(db_top, db_body, db_bottom).scale(0.6)

        # Arrow
        arrow = Arrow(
            start=LEFT * 0.5, end=RIGHT * 0.5,
            color=PRIMARY_COLOR, stroke_width=8,
            max_tip_length_to_length_ratio=0.3
        ).scale(1.5)

        # dbt icon (transformation gear)
        dbt_icon = VGroup()
        gear = RegularPolygon(n=6, color=DBT_COLOR, fill_opacity=0.8).scale(0.5)
        inner_circle = Circle(radius=0.15, color=BACKGROUND_COLOR, fill_opacity=1)
        dbt_icon.add(gear, inner_circle)

        # Position icons
        ssis_db.shift(LEFT * 2.5)
        dbt_icon.shift(RIGHT * 2.5)

        # Main logo group
        logo_group = VGroup(ssis_db, arrow, dbt_icon)
        logo_group.shift(UP * 0.5)

        # Title
        title = Text(
            "SSIS-to-dbt",
            font="JetBrains Mono",
            font_size=72,
            color=TEXT_COLOR
        ).next_to(logo_group, DOWN, buff=0.8)

        subtitle = Text(
            "Migration Factory",
            font="JetBrains Mono",
            font_size=48,
            color=PRIMARY_COLOR
        ).next_to(title, DOWN, buff=0.2)

        tagline = Text(
            "Automated SSIS Package Conversion",
            font="JetBrains Mono",
            font_size=24,
            color=DIM_TEXT_COLOR
        ).next_to(subtitle, DOWN, buff=0.5)

        # Animations
        self.play(
            Create(ssis_db, run_time=1),
            Create(dbt_icon, run_time=1),
        )
        self.play(
            GrowArrow(arrow),
            run_time=0.8
        )
        self.play(
            Write(title),
            run_time=1
        )
        self.play(
            FadeIn(subtitle, shift=UP * 0.2),
            run_time=0.6
        )
        self.play(
            FadeIn(tagline, shift=UP * 0.2),
            run_time=0.5
        )

        self.wait(2)

        # Fade out
        self.play(
            FadeOut(logo_group),
            FadeOut(title),
            FadeOut(subtitle),
            FadeOut(tagline),
            run_time=0.8
        )

    # =========================================================================
    # SCENE 2: THE PROBLEM
    # =========================================================================
    def play_problem_statement(self):
        """Show the problem this tool solves."""
        # Header
        header = Text(
            "The Challenge",
            font="JetBrains Mono",
            font_size=48,
            color=PRIMARY_COLOR
        ).to_edge(UP, buff=0.5)

        # Problem cards
        problems = [
            ("Manual", "Manual conversion is slow & error-prone"),
            ("Complex", "SSIS XML is deeply nested & complex"),
            ("Validation", "Hard to verify data integrity after migration"),
        ]

        problem_cards = VGroup()
        for i, (icon_text, desc) in enumerate(problems):
            card = self.create_card(icon_text, desc, ACCENT_COLOR)
            problem_cards.add(card)

        problem_cards.arrange(DOWN, buff=0.4)
        problem_cards.next_to(header, DOWN, buff=0.6)

        # Animations
        self.play(Write(header))
        self.wait(0.3)

        for card in problem_cards:
            self.play(FadeIn(card, shift=RIGHT * 0.3), run_time=0.5)
            self.wait(0.4)

        self.wait(1.5)

        # Transition: Show solution
        solution_text = Text(
            "We automate this.",
            font="JetBrains Mono",
            font_size=36,
            color=SECONDARY_COLOR
        ).move_to(ORIGIN)

        self.play(
            FadeOut(problem_cards),
            FadeOut(header),
            run_time=0.5
        )
        self.play(Write(solution_text), run_time=0.8)
        self.wait(1)
        self.play(FadeOut(solution_text))

    def create_card(self, icon_text: str, description: str, color: str) -> VGroup:
        """Create a styled info card."""
        card_bg = RoundedRectangle(
            width=10, height=1.2,
            corner_radius=0.15,
            color=color,
            fill_opacity=0.15,
            stroke_width=2
        )

        icon = Text(
            icon_text,
            font="JetBrains Mono",
            font_size=20,
            color=color
        ).move_to(card_bg.get_left() + RIGHT * 1)

        desc = Text(
            description,
            font="JetBrains Mono",
            font_size=22,
            color=TEXT_COLOR
        ).next_to(icon, RIGHT, buff=0.5)

        return VGroup(card_bg, icon, desc)

    # =========================================================================
    # SCENE 3: ARCHITECTURE OVERVIEW
    # =========================================================================
    def play_architecture(self):
        """Animated architecture diagram."""
        header = Text(
            "How It Works",
            font="JetBrains Mono",
            font_size=48,
            color=PRIMARY_COLOR
        ).to_edge(UP, buff=0.5)

        self.play(Write(header))

        # Create flow diagram
        # Phase boxes
        phases = [
            ("1. Parse", "SSIS Parser", SSIS_COLOR, "Extract XML\nmetadata"),
            ("2. Analyze", "AI Agents", PYTHON_COLOR, "Pattern\ndetection"),
            ("3. Generate", "dbt Builder", DBT_COLOR, "Create SQL\nmodels"),
            ("4. Validate", "Validator", SECONDARY_COLOR, "Data quality\nchecks"),
        ]

        flow_items = VGroup()
        arrows = VGroup()

        for i, (phase, name, color, desc) in enumerate(phases):
            box = self.create_phase_box(phase, name, desc, color)
            flow_items.add(box)

        flow_items.arrange(RIGHT, buff=1.2)
        flow_items.next_to(header, DOWN, buff=1)

        # Create arrows between phases
        for i in range(len(flow_items) - 1):
            arrow = Arrow(
                start=flow_items[i].get_right(),
                end=flow_items[i + 1].get_left(),
                color=DIM_TEXT_COLOR,
                stroke_width=3,
                max_tip_length_to_length_ratio=0.2,
                buff=0.1
            )
            arrows.add(arrow)

        # Animate phases appearing one by one
        for i, (box, phase_data) in enumerate(zip(flow_items, phases)):
            self.play(Create(box), run_time=0.6)
            if i < len(arrows):
                self.play(GrowArrow(arrows[i]), run_time=0.3)
            self.wait(0.3)

        # Add detail panel
        detail_box = RoundedRectangle(
            width=12, height=2,
            corner_radius=0.2,
            color=PRIMARY_COLOR,
            fill_opacity=0.1,
            stroke_width=1
        ).next_to(flow_items, DOWN, buff=0.8)

        detail_items = VGroup(
            Text("3 SSIS Packages", font="JetBrains Mono", font_size=20, color=SSIS_COLOR),
            Text("→", font="JetBrains Mono", font_size=20, color=DIM_TEXT_COLOR),
            Text("11 Tasks Extracted", font="JetBrains Mono", font_size=20, color=PYTHON_COLOR),
            Text("→", font="JetBrains Mono", font_size=20, color=DIM_TEXT_COLOR),
            Text("7 dbt Models", font="JetBrains Mono", font_size=20, color=DBT_COLOR),
            Text("→", font="JetBrains Mono", font_size=20, color=DIM_TEXT_COLOR),
            Text("100% Validated", font="JetBrains Mono", font_size=20, color=SECONDARY_COLOR),
        ).arrange(RIGHT, buff=0.3)
        detail_items.move_to(detail_box)

        self.play(Create(detail_box), run_time=0.4)
        self.play(Write(detail_items), run_time=1)

        self.wait(2)

        # Cleanup
        self.play(
            FadeOut(header),
            FadeOut(flow_items),
            FadeOut(arrows),
            FadeOut(detail_box),
            FadeOut(detail_items),
            run_time=0.6
        )

    def create_phase_box(self, phase: str, name: str, desc: str, color: str) -> VGroup:
        """Create a phase box for the architecture diagram."""
        box = RoundedRectangle(
            width=2.4, height=3,
            corner_radius=0.15,
            color=color,
            fill_opacity=0.2,
            stroke_width=2
        )

        phase_text = Text(
            phase,
            font="JetBrains Mono",
            font_size=14,
            color=color
        ).next_to(box.get_top(), DOWN, buff=0.2)

        name_text = Text(
            name,
            font="JetBrains Mono",
            font_size=18,
            color=TEXT_COLOR
        ).next_to(phase_text, DOWN, buff=0.3)

        desc_text = Text(
            desc,
            font="JetBrains Mono",
            font_size=12,
            color=DIM_TEXT_COLOR,
            line_spacing=1.2
        ).next_to(name_text, DOWN, buff=0.3)

        return VGroup(box, phase_text, name_text, desc_text)

    # =========================================================================
    # SCENE 4: CODE HIGHLIGHT
    # =========================================================================
    def play_code_highlight(self):
        """Show key code transformation."""
        header = Text(
            "SSIS → dbt Transformation",
            font="JetBrains Mono",
            font_size=40,
            color=PRIMARY_COLOR
        ).to_edge(UP, buff=0.5)

        self.play(Write(header))

        # Left panel: SSIS concept
        ssis_label = Text(
            "SSIS Lookup Transform",
            font="JetBrains Mono",
            font_size=16,
            color=SSIS_COLOR
        )

        ssis_code = Code(
            code='''<!-- Lookup Customer Dimension -->
<component name="Lookup Customer">
  <properties>
    <property name="SqlCommand">
      SELECT CustomerKey, CustomerID
      FROM dim.Customer
      WHERE IsActive = 1
    </property>
    <property name="NoMatchBehavior">
      REDIRECT_TO_NO_MATCH_OUTPUT
    </property>
  </properties>
</component>''',
            language="xml",
            font="JetBrains Mono",
            font_size=14,
            background="rectangle",
            background_stroke_color=SSIS_COLOR,
            insert_line_no=False,
            style="monokai"
        ).scale(0.7)

        ssis_panel = VGroup(ssis_label, ssis_code).arrange(DOWN, buff=0.3)
        ssis_panel.shift(LEFT * 3.5 + DOWN * 0.3)

        # Right panel: dbt code
        dbt_label = Text(
            "Generated dbt Model",
            font="JetBrains Mono",
            font_size=16,
            color=DBT_COLOR
        )

        dbt_code = Code(
            code='''-- Lookup Customer (dbt JOIN)
WITH sales AS (
    SELECT * FROM {{ ref('stg_sales') }}
),

with_customer AS (
    SELECT
        s.*,
        c.customer_key
    FROM sales s
    LEFT JOIN {{ ref('dim_customer') }} c
        ON s.customer_id = c.customer_id
        AND c.is_current = 1
)

SELECT * FROM with_customer''',
            language="sql",
            font="JetBrains Mono",
            font_size=14,
            background="rectangle",
            background_stroke_color=DBT_COLOR,
            insert_line_no=False,
            style="monokai"
        ).scale(0.7)

        dbt_panel = VGroup(dbt_label, dbt_code).arrange(DOWN, buff=0.3)
        dbt_panel.shift(RIGHT * 3.5 + DOWN * 0.3)

        # Transform arrow
        transform_arrow = Arrow(
            start=ssis_panel.get_right() + LEFT * 0.5,
            end=dbt_panel.get_left() + RIGHT * 0.5,
            color=PRIMARY_COLOR,
            stroke_width=4
        )

        transform_text = Text(
            "Auto-convert",
            font="JetBrains Mono",
            font_size=14,
            color=PRIMARY_COLOR
        ).next_to(transform_arrow, UP, buff=0.1)

        # Animations
        self.play(FadeIn(ssis_panel, shift=RIGHT * 0.3), run_time=0.8)
        self.wait(1.5)

        self.play(
            GrowArrow(transform_arrow),
            Write(transform_text),
            run_time=0.6
        )

        self.play(FadeIn(dbt_panel, shift=LEFT * 0.3), run_time=0.8)
        self.wait(2)

        # Highlight key transformation
        highlight_box = SurroundingRectangle(
            dbt_code[6:10] if hasattr(dbt_code, '__getitem__') else dbt_code,
            color=SECONDARY_COLOR,
            buff=0.1,
            stroke_width=2
        )

        # Cleanup
        self.play(
            FadeOut(header),
            FadeOut(ssis_panel),
            FadeOut(dbt_panel),
            FadeOut(transform_arrow),
            FadeOut(transform_text),
            run_time=0.6
        )

    # =========================================================================
    # SCENE 5: TERMINAL DEMO
    # =========================================================================
    def play_terminal_demo(self):
        """Simulate terminal execution."""
        header = Text(
            "Quick Start",
            font="JetBrains Mono",
            font_size=48,
            color=PRIMARY_COLOR
        ).to_edge(UP, buff=0.5)

        self.play(Write(header))

        # Terminal window
        terminal_bg = RoundedRectangle(
            width=12, height=5.5,
            corner_radius=0.2,
            color=TERMINAL_BG,
            fill_opacity=1,
            stroke_color=DIM_TEXT_COLOR,
            stroke_width=1
        ).next_to(header, DOWN, buff=0.5)

        # Terminal title bar
        title_bar = Rectangle(
            width=12, height=0.4,
            color="#1f2428",
            fill_opacity=1
        ).next_to(terminal_bg.get_top(), DOWN, buff=0)

        # Window buttons
        buttons = VGroup(
            Circle(radius=0.08, color="#ff5f57", fill_opacity=1),
            Circle(radius=0.08, color="#febc2e", fill_opacity=1),
            Circle(radius=0.08, color="#28c840", fill_opacity=1),
        ).arrange(RIGHT, buff=0.15)
        buttons.move_to(title_bar.get_left() + RIGHT * 0.5)

        title_text = Text(
            "Terminal — bash",
            font="JetBrains Mono",
            font_size=12,
            color=DIM_TEXT_COLOR
        ).move_to(title_bar)

        terminal_frame = VGroup(terminal_bg, title_bar, buttons, title_text)

        self.play(Create(terminal_frame), run_time=0.5)

        # Terminal content area
        content_start = terminal_bg.get_top() + DOWN * 0.8 + LEFT * 5.5

        # Command prompt and output
        lines = [
            ("$ ", "python run_agents.py ./samples/ssis_packages --auto-approve", PRIMARY_COLOR),
            ("", "", None),
            ("[INFO] ", "Parsing SSIS packages...", TEXT_COLOR),
            ("[INFO] ", "  → CustomerDataLoad.dtsx", DIM_TEXT_COLOR),
            ("[INFO] ", "  → SalesFactETL.dtsx", DIM_TEXT_COLOR),
            ("[INFO] ", "  → InventorySync.dtsx", DIM_TEXT_COLOR),
            ("", "", None),
            ("[INFO] ", "Analyzing 11 tasks...", TEXT_COLOR),
            ("[WARN] ", "Script Task 'Call Inventory API' flagged for manual review", ACCENT_COLOR),
            ("", "", None),
            ("[INFO] ", "Generating dbt models...", TEXT_COLOR),
            ("[SUCCESS] ", "Generated 7 dbt models", SECONDARY_COLOR),
            ("[SUCCESS] ", "Created 4 source YAML files", SECONDARY_COLOR),
            ("", "", None),
            ("[SUCCESS] ", "Migration complete! 63.6% auto-converted", SECONDARY_COLOR),
        ]

        terminal_lines = VGroup()
        y_offset = 0

        for prefix, text, color in lines:
            if not text and not prefix:
                y_offset += 0.3
                continue

            line_group = VGroup()

            if prefix:
                prefix_text = Text(
                    prefix,
                    font="JetBrains Mono",
                    font_size=14,
                    color=color if "SUCCESS" in prefix else (ACCENT_COLOR if "WARN" in prefix else DIM_TEXT_COLOR)
                )
                line_group.add(prefix_text)

            main_text = Text(
                text,
                font="JetBrains Mono",
                font_size=14,
                color=color or TEXT_COLOR
            )

            if prefix:
                main_text.next_to(prefix_text, RIGHT, buff=0.05)
            line_group.add(main_text)

            line_group.move_to(content_start + DOWN * y_offset, aligned_edge=LEFT)
            terminal_lines.add(line_group)
            y_offset += 0.35

        # Animate typing effect
        for i, line in enumerate(terminal_lines):
            if i == 0:
                # Type the command character by character effect
                self.play(Write(line), run_time=1.2)
                self.wait(0.3)
            else:
                self.play(FadeIn(line, shift=UP * 0.1), run_time=0.15)

        self.wait(2)

        # Cleanup
        self.play(
            FadeOut(header),
            FadeOut(terminal_frame),
            FadeOut(terminal_lines),
            run_time=0.6
        )

    # =========================================================================
    # SCENE 6: RESULTS
    # =========================================================================
    def play_results(self):
        """Show the results dashboard."""
        header = Text(
            "Migration Results",
            font="JetBrains Mono",
            font_size=48,
            color=PRIMARY_COLOR
        ).to_edge(UP, buff=0.5)

        self.play(Write(header))

        # Stats cards
        stats = [
            ("3", "SSIS\nPackages", SSIS_COLOR),
            ("11", "Tasks\nExtracted", PYTHON_COLOR),
            ("7", "dbt Models\nGenerated", DBT_COLOR),
            ("63.6%", "Auto\nConverted", SECONDARY_COLOR),
        ]

        stat_cards = VGroup()
        for value, label, color in stats:
            card = self.create_stat_card(value, label, color)
            stat_cards.add(card)

        stat_cards.arrange(RIGHT, buff=0.5)
        stat_cards.next_to(header, DOWN, buff=0.8)

        for card in stat_cards:
            self.play(FadeIn(card, scale=0.8), run_time=0.4)

        self.wait(0.5)

        # Validation results table
        table_header = Text(
            "Validation Summary",
            font="JetBrains Mono",
            font_size=24,
            color=TEXT_COLOR
        ).next_to(stat_cards, DOWN, buff=0.8)

        self.play(Write(table_header))

        validation_data = [
            ("dim_customer", "15,234", "15,234", "PASS", SECONDARY_COLOR),
            ("fct_sales", "1,250,847", "1,250,847", "PASS", SECONDARY_COLOR),
            ("fct_inventory", "45,892", "45,892", "PASS", SECONDARY_COLOR),
            ("agg_daily_sales", "8,547", "8,547", "PASS", SECONDARY_COLOR),
        ]

        table = self.create_validation_table(validation_data)
        table.next_to(table_header, DOWN, buff=0.4)

        self.play(Create(table), run_time=1)

        self.wait(2)

        # Cleanup
        self.play(
            FadeOut(header),
            FadeOut(stat_cards),
            FadeOut(table_header),
            FadeOut(table),
            run_time=0.6
        )

    def create_stat_card(self, value: str, label: str, color: str) -> VGroup:
        """Create a statistics card."""
        card_bg = RoundedRectangle(
            width=2.5, height=2.5,
            corner_radius=0.15,
            color=color,
            fill_opacity=0.15,
            stroke_width=2
        )

        value_text = Text(
            value,
            font="JetBrains Mono",
            font_size=36,
            color=color
        ).move_to(card_bg.get_center() + UP * 0.3)

        label_text = Text(
            label,
            font="JetBrains Mono",
            font_size=14,
            color=DIM_TEXT_COLOR,
            line_spacing=1.2
        ).next_to(value_text, DOWN, buff=0.2)

        return VGroup(card_bg, value_text, label_text)

    def create_validation_table(self, data: list) -> VGroup:
        """Create a validation results table."""
        table = VGroup()

        # Header row
        headers = ["Model", "Legacy", "dbt", "Status"]
        header_row = VGroup()
        x_positions = [-3, -0.5, 1.5, 3.5]

        for i, (header, x_pos) in enumerate(zip(headers, x_positions)):
            text = Text(
                header,
                font="JetBrains Mono",
                font_size=14,
                color=DIM_TEXT_COLOR
            )
            text.move_to(RIGHT * x_pos)
            header_row.add(text)

        table.add(header_row)

        # Data rows
        for row_idx, (model, legacy, dbt_val, status, color) in enumerate(data):
            row = VGroup()
            values = [model, legacy, dbt_val, status]

            for i, (val, x_pos) in enumerate(zip(values, x_positions)):
                text_color = color if i == 3 else TEXT_COLOR
                text = Text(
                    val,
                    font="JetBrains Mono",
                    font_size=14,
                    color=text_color
                )
                text.move_to(RIGHT * x_pos + DOWN * (row_idx + 1) * 0.5)
                row.add(text)

            table.add(row)

        table.move_to(ORIGIN)
        return table

    # =========================================================================
    # SCENE 7: OUTRO
    # =========================================================================
    def play_outro(self):
        """GitHub-style outro with call to action."""
        # Logo recreation (smaller)
        arrow = Arrow(
            start=LEFT * 0.3, end=RIGHT * 0.3,
            color=PRIMARY_COLOR, stroke_width=6
        )

        title = Text(
            "SSIS-to-dbt Migration Factory",
            font="JetBrains Mono",
            font_size=36,
            color=TEXT_COLOR
        ).next_to(arrow, DOWN, buff=0.5)

        logo_group = VGroup(arrow, title)
        logo_group.shift(UP * 1.5)

        self.play(
            GrowArrow(arrow),
            Write(title),
            run_time=1
        )

        # Get Started section
        get_started = Text(
            "Get Started",
            font="JetBrains Mono",
            font_size=28,
            color=SECONDARY_COLOR
        ).next_to(title, DOWN, buff=0.8)

        self.play(FadeIn(get_started, shift=UP * 0.2))

        # Command box
        cmd_bg = RoundedRectangle(
            width=10, height=0.8,
            corner_radius=0.1,
            color=TERMINAL_BG,
            fill_opacity=1,
            stroke_color=DIM_TEXT_COLOR,
            stroke_width=1
        ).next_to(get_started, DOWN, buff=0.4)

        cmd_text = Text(
            "git clone https://github.com/wiederMatan/ssis-to-dbt",
            font="JetBrains Mono",
            font_size=16,
            color=TEXT_COLOR
        ).move_to(cmd_bg)

        self.play(
            Create(cmd_bg),
            Write(cmd_text),
            run_time=0.8
        )

        # Features list
        features = VGroup(
            Text("Parse SSIS packages automatically", font="JetBrains Mono", font_size=16, color=DIM_TEXT_COLOR),
            Text("Generate production-ready dbt models", font="JetBrains Mono", font_size=16, color=DIM_TEXT_COLOR),
            Text("Validate data integrity", font="JetBrains Mono", font_size=16, color=DIM_TEXT_COLOR),
            Text("Monitor with React dashboard", font="JetBrains Mono", font_size=16, color=DIM_TEXT_COLOR),
        ).arrange(DOWN, buff=0.25, aligned_edge=LEFT)

        # Add checkmarks
        for feature in features:
            check = Text("✓ ", font="JetBrains Mono", font_size=16, color=SECONDARY_COLOR)
            check.next_to(feature, LEFT, buff=0.1)
            feature.add_to_back(check)

        features.next_to(cmd_bg, DOWN, buff=0.6)

        self.play(
            LaggedStart(
                *[FadeIn(f, shift=RIGHT * 0.2) for f in features],
                lag_ratio=0.15
            ),
            run_time=1.2
        )

        # Star CTA
        star_text = Text(
            "Star the repo if this helped you!",
            font="JetBrains Mono",
            font_size=18,
            color=PRIMARY_COLOR
        ).next_to(features, DOWN, buff=0.6)

        star_icon = Text(
            "★",
            font_size=24,
            color="#f1e05a"  # GitHub star yellow
        ).next_to(star_text, LEFT, buff=0.2)

        self.play(
            FadeIn(star_text),
            FadeIn(star_icon),
            run_time=0.6
        )

        self.wait(3)

        # Final fade
        self.play(
            *[FadeOut(mob) for mob in self.mobjects],
            run_time=1
        )


# =============================================================================
# OPTIONAL: Individual scene classes for testing
# =============================================================================
class IntroScene(Scene):
    """Just the intro for testing."""

    def construct(self):
        self.camera.background_color = BACKGROUND_COLOR
        main = SSIStoDBTExplainer()
        main.camera = self.camera
        main.play_intro = lambda: SSIStoDBTExplainer.play_intro(self)
        SSIStoDBTExplainer.play_intro(self)


class ArchitectureScene(Scene):
    """Just the architecture for testing."""

    def construct(self):
        self.camera.background_color = BACKGROUND_COLOR
        explainer = SSIStoDBTExplainer()
        explainer.camera = self.camera
        # Create necessary methods
        self.create_phase_box = explainer.create_phase_box
        explainer.play_architecture(self)


# =============================================================================
# RUN INSTRUCTIONS
# =============================================================================
if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║           SSIS-to-dbt Migration Factory - Manim Explainer Video           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  RENDER COMMANDS:                                                         ║
║                                                                           ║
║  Full video (1080p):                                                      ║
║    manim -pqh docs/manim_explainer.py SSIStoDBTExplainer                  ║
║                                                                           ║
║  Preview (480p, faster):                                                  ║
║    manim -pql docs/manim_explainer.py SSIStoDBTExplainer                  ║
║                                                                           ║
║  4K render:                                                               ║
║    manim -pqk docs/manim_explainer.py SSIStoDBTExplainer                  ║
║                                                                           ║
║  Output location: media/videos/manim_explainer/                           ║
║                                                                           ║
║  REQUIREMENTS:                                                            ║
║    pip install manim                                                      ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
