"""Prompt templates for content generation."""

from typing import Dict, Optional


def get_content_generation_system_prompt(
    brand_tone: Optional[str] = None,
    project_context: Optional[str] = None,
) -> str:
    """Get system prompt for content generation.

    Args:
        brand_tone: Brand tone and style guidelines
        project_context: Additional project context

    Returns:
        str: System prompt for content generation
    """
    base_prompt = """You are a helpful marketing copy assistant. Your role is to create engaging,
 effective marketing content that aligns with brand guidelines and resonates with target audiences.

Guidelines:
- Write in a clear, professional, and engaging tone
- Focus on the audience's needs and interests
- Include compelling calls-to-action when appropriate
- Maintain brand consistency across all content
- Be concise but informative
- Use active voice and strong verbs"""

    if brand_tone:
        base_prompt += f"\n\nBrand Tone and Style:\n{brand_tone}"

    if project_context:
        base_prompt += f"\n\nProject Context:\n{project_context}"

    return base_prompt


def get_short_form_prompt(brief: str, brand_tone: Optional[str] = None) -> str:
    """Get prompt for short-form content generation.

    Args:
        brief: Campaign brief/description
        brand_tone: Brand tone guidelines

    Returns:
        str: Prompt for short-form generation
    """
    prompt = f"""Generate a short-form social media post based on the following brief:

Brief: {brief}

Requirements:
- Maximum 200 characters
- Engaging and attention-grabbing
- Include relevant hashtags if appropriate
- Clear call-to-action
- Optimized for social media engagement"""

    if brand_tone:
        prompt += f"\n\nBrand Tone: {brand_tone}"

    return prompt


def get_long_form_prompt(brief: str, brand_tone: Optional[str] = None) -> str:
    """Get prompt for long-form content generation.

    Args:
        brief: Campaign brief/description
        brand_tone: Brand tone guidelines

    Returns:
        str: Prompt for long-form generation
    """
    prompt = f"""Generate a long-form marketing post based on the following brief:

Brief: {brief}

Requirements:
- 150-300 words
- Comprehensive and informative
- Well-structured with clear sections
- Engaging narrative flow
- Include key messaging points
- Professional yet approachable tone"""

    if brand_tone:
        prompt += f"\n\nBrand Tone: {brand_tone}"

    return prompt


def get_cta_prompt(brief: str, brand_tone: Optional[str] = None) -> str:
    """Get prompt for CTA (call-to-action) content generation.

    Args:
        brief: Campaign brief/description
        brand_tone: Brand tone guidelines

    Returns:
        str: Prompt for CTA generation
    """
    prompt = f"""Generate a call-to-action focused marketing message based on the following brief:

Brief: {brief}

Requirements:
- Compelling subject line (if email) or headline
- Strong, clear call-to-action
- Urgency or value proposition
- Action-oriented language
- Concise but persuasive
- Include specific next steps"""

    if brand_tone:
        prompt += f"\n\nBrand Tone: {brand_tone}"

    return prompt


def build_project_context(
    project_name: Optional[str] = None,
    project_description: Optional[str] = None,
    asset_summaries: Optional[list] = None,
) -> str:
    """Build project context string from project information.

    Args:
        project_name: Name of the project
        project_description: Project description
        asset_summaries: List of asset summaries/metadata

    Returns:
        str: Formatted project context
    """
    context_parts = []

    if project_name:
        context_parts.append(f"Project: {project_name}")

    if project_description:
        context_parts.append(f"Description: {project_description}")

    if asset_summaries:
        context_parts.append("\nAvailable Assets:")
        for asset in asset_summaries:
            asset_info = f"- {asset.get('filename', 'Unknown')}"
            if asset.get("content_type"):
                asset_info += f" ({asset.get('content_type')})"
            context_parts.append(asset_info)

    return "\n".join(context_parts) if context_parts else ""
