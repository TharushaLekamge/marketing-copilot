"""Semantic Kernel prompt templates for content generation."""

# These are prompt templates that will be used by Semantic Kernel
# They use Handlebars template syntax with {{variables}}

SHORT_FORM_TEMPLATE = """
<message role="system">{{system_message}}</message>

Generate a short-form social media post based on this brief:

Brief: {{brief}}

Requirements:
- Maximum 100 characters
- Engaging and attention-grabbing
- Include relevant hashtags if appropriate
- Clear call-to-action
- Optimized for social media engagement

{{#if brand_tone}}
Brand Tone: {{brand_tone}}
{{/if}}

{{#if context}}
Context: {{context}}
{{/if}}"""

LONG_FORM_TEMPLATE = """
<message role="system">{{system_message}}</message>

Generate a long-form marketing post based on this brief:

Brief: {{brief}}

Requirements:
- 150-300 words
- Comprehensive and informative
- Well-structured with clear sections
- Engaging narrative flow
- Include key messaging points
- Professional yet approachable tone

{{#if brand_tone}}
Brand Tone: {{brand_tone}}
{{/if}}

{{#if context}}
Context: {{context}}
{{/if}}"""

CTA_TEMPLATE = """
<message role="system">{{system_message}}</message>

Generate a call-to-action focused marketing message based on this brief:

Brief: {{brief}}

Requirements:
- Compelling subject line (if email) or headline
- Strong, clear call-to-action
- Urgency or value proposition
- Action-oriented language
- Concise but persuasive
- Include specific next steps

{{#if brand_tone}}
Brand Tone: {{brand_tone}}
{{/if}}

{{#if context}}
Context: {{context}}
{{/if}}"""
