import os
import textwrap
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.models.schemas import CreativeCopy


class AdCompositor:
    """
    High-reliability deterministic visual compositor.
    Combines AI-generated creative copy, atmospheric scene background,
    and unaltered source product imagery into a publication-ready ad.
    """

    def __init__(self, canvas_width: int = 1080, canvas_height: int = 1080):
        self.width = canvas_width
        self.height = canvas_height

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """
        Attempts to load standard system TrueType fonts with seamless cross-platform fallbacks.
        Works across macOS, Linux (Docker), and Windows.
        """
        candidate_paths = [
            # Linux Debian / Ubuntu (standard Docker base)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            # Windows
            "C:\\Windows\\Fonts\\arial.ttf",
        ]

        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    continue

        # Fallback to default built-in font
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def _render_scrim(self, base_image: Image.Image) -> Image.Image:
        """
        Adds subtle gradient scrims at top and bottom to guarantee
        text and CTA button legibility over any background.
        """
        scrim = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(scrim)

        # Top dark scrim for copy readability
        top_scrim_height = int(self.height * 0.42)
        for y in range(top_scrim_height):
            alpha = int(190 * (1.0 - (y / top_scrim_height) ** 1.3))
            draw.line([(0, y), (self.width, y)], fill=(10, 15, 20, alpha))

        # Bottom subtle scrim for CTA anchor
        bottom_scrim_start = int(self.height * 0.75)
        for y in range(bottom_scrim_start, self.height):
            t = (y - bottom_scrim_start) / float(self.height - bottom_scrim_start)
            alpha = int(160 * (t ** 1.2))
            draw.line([(0, y), (self.width, y)], fill=(10, 15, 20, alpha))

        return Image.alpha_composite(base_image.convert("RGBA"), scrim)

    def _render_product(
        self,
        base_image: Image.Image,
        product_img: Image.Image
    ) -> Image.Image:
        """
        Positions the original source product recognizably with a soft ambient drop shadow.
        """
        # Desired product bounding box: centered horizontally, vertically in lower-middle
        max_p_width = int(self.width * 0.58)
        max_p_height = int(self.height * 0.48)

        p_copy = product_img.copy()
        p_copy.thumbnail((max_p_width, max_p_height), Image.Resampling.LANCZOS)
        pw, ph = p_copy.size

        # Center product horizontally, align in mid-lower section
        px = (self.width - pw) // 2
        py = int(self.height * 0.40) + (max_p_height - ph) // 2

        # Generate soft ambient drop shadow beneath product
        shadow_canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_canvas)

        shadow_w = int(pw * 0.75)
        shadow_h = int(ph * 0.14)
        shadow_x0 = (self.width - shadow_w) // 2
        shadow_y0 = py + ph - int(shadow_h * 0.4)

        shadow_draw.ellipse(
            [shadow_x0, shadow_y0, shadow_x0 + shadow_w, shadow_y0 + shadow_h],
            fill=(0, 0, 0, 140)
        )
        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=22))

        # Composite shadow then product
        composed = Image.alpha_composite(base_image, shadow_canvas)
        composed.paste(p_copy, (px, py), p_copy if p_copy.mode == "RGBA" else None)
        return composed

    def _render_text_and_cta(
        self,
        base_image: Image.Image,
        product_name: str,
        creative_copy: CreativeCopy,
        tone: str,
    ) -> Image.Image:
        """
        Renders category badge, bold headline, supporting text, and high-converting CTA button.
        """
        img = base_image.copy()
        draw = ImageDraw.Draw(img)

        # 1. Category / Brand Pill Tag
        tag_text = product_name.upper()
        tag_font = self._get_font(20, bold=True)
        tag_x = 70
        tag_y = 65

        # Render sleek pill for tag
        tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
        tag_w = tag_bbox[2] - tag_bbox[0]
        tag_h = tag_bbox[3] - tag_bbox[1]
        pill_pad_x = 18
        pill_pad_y = 8
        pill_rect = [
            tag_x - pill_pad_x,
            tag_y - pill_pad_y,
            tag_x + tag_w + pill_pad_x,
            tag_y + tag_h + pill_pad_y + 2
        ]
        draw.rounded_rectangle(pill_rect, radius=14, fill=(255, 255, 255, 35), outline=(255, 255, 255, 70), width=1)
        draw.text((tag_x, tag_y), tag_text, font=tag_font, fill=(240, 245, 255, 240))

        # 2. Headline (Bold, high impact, <= 8 words)
        headline_font = self._get_font(52, bold=True)
        headline_lines = textwrap.wrap(creative_copy.headline, width=28)
        headline_y = tag_y + 55

        for line in headline_lines[:2]:  # Keep to 2 lines max
            # Drop shadow for headline
            draw.text((tag_x + 2, headline_y + 2), line, font=headline_font, fill=(0, 0, 0, 180))
            draw.text((tag_x, headline_y), line, font=headline_font, fill=(255, 255, 255, 255))
            bbox = draw.textbbox((0, 0), line, font=headline_font)
            headline_y += (bbox[3] - bbox[1]) + 12

        # 3. Supporting Text (Clean, legible, <= 20 words)
        support_font = self._get_font(27, bold=False)
        support_lines = textwrap.wrap(creative_copy.supporting_text, width=46)
        support_y = headline_y + 8

        for line in support_lines[:3]:  # Keep to 3 lines max
            draw.text((tag_x + 1, support_y + 1), line, font=support_font, fill=(0, 0, 0, 160))
            draw.text((tag_x, support_y), line, font=support_font, fill=(225, 232, 240, 240))
            bbox = draw.textbbox((0, 0), line, font=support_font)
            support_y += (bbox[3] - bbox[1]) + 8

        # 4. CTA Button (Bottom Center/Left)
        cta_font = self._get_font(26, bold=True)
        cta_text = f"{creative_copy.cta}  →"
        cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        cta_text_w = cta_bbox[2] - cta_bbox[0]
        cta_text_h = cta_bbox[3] - cta_bbox[1]

        cta_btn_w = max(260, cta_text_w + 60)
        cta_btn_h = 64
        cta_x = (self.width - cta_btn_w) // 2
        cta_y = self.height - cta_btn_h - 70

        # CTA Button Shadow
        cta_shadow = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        cta_sdraw = ImageDraw.Draw(cta_shadow)
        cta_sdraw.rounded_rectangle(
            [cta_x + 2, cta_y + 6, cta_x + cta_btn_w + 2, cta_y + cta_btn_h + 6],
            radius=32,
            fill=(0, 0, 0, 120)
        )
        cta_shadow = cta_shadow.filter(ImageFilter.GaussianBlur(radius=10))
        img = Image.alpha_composite(img, cta_shadow)
        draw = ImageDraw.Draw(img)

        # Dynamic CTA color accent based on tone
        tone_l = tone.lower()
        if "adventurous" in tone_l or "outdoor" in tone_l:
            btn_color = (245, 158, 11)   # Vibrant amber
            text_color = (15, 23, 42)
        elif "luxury" in tone_l or "serum" in tone_l:
            btn_color = (255, 237, 213)  # Champagne rose
            text_color = (28, 25, 23)
        elif "tech" in tone_l or "audio" in tone_l:
            btn_color = (56, 189, 248)   # Electric sky cyan
            text_color = (15, 23, 42)
        else:
            btn_color = (255, 255, 255)   # Crisp white
            text_color = (15, 23, 42)

        draw.rounded_rectangle(
            [cta_x, cta_y, cta_x + cta_btn_w, cta_y + cta_btn_h],
            radius=32,
            fill=btn_color
        )

        # Center CTA text inside pill
        tx = cta_x + (cta_btn_w - cta_text_w) // 2
        ty = cta_y + (cta_btn_h - cta_text_h) // 2 - 2
        draw.text((tx, ty), cta_text, font=cta_font, fill=text_color)

        return img

    def compose_ad(
        self,
        background: Image.Image,
        product_image: Image.Image,
        product_name: str,
        creative_copy: CreativeCopy,
        tone: str,
        output_path: str,
    ) -> str:
        """
        Orchestrates full composite pipeline and saves the finished ad image.
        """
        bg_resized = background.resize((self.width, self.height), Image.Resampling.LANCZOS)
        scrimmed = self._render_scrim(bg_resized)
        with_product = self._render_product(scrimmed, product_image)
        final_ad = self._render_text_and_cta(with_product, product_name, creative_copy, tone)

        # Ensure directory exists and save as PNG
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        final_ad.convert("RGB").save(output_path, format="PNG", quality=95, optimize=True)
        return output_path
