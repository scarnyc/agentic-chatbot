#!/usr/bin/env python3
"""
MCP Server for writing assistance tools.
Provides specialized writing capabilities using GPT-4o-mini for various content types.
"""

import logging
import os
import sys
import re
from typing import Optional

# Add parent directory to path first
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from mcp.mcp_server_base import FastMCP

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("writing-server")

# Create FastMCP server
mcp = FastMCP("Writing Server")

# Initialize OpenAI client
openai_client = None
if HAS_OPENAI:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            openai_client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized for writing assistance")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            openai_client = None
    else:
        logger.warning("OPENAI_API_KEY not found - writing assistance will be limited")

def detect_writing_request(prompt: str) -> tuple[bool, str]:
    """
    Detect if a prompt contains a writing request and identify the type.
    
    Args:
        prompt: User prompt to analyze
        
    Returns:
        Tuple of (is_writing_request, writing_type)
    """
    prompt_lower = prompt.lower()
    
    # Writing keywords and their types
    writing_patterns = {
        'email': r'\b(email|e-mail|message|send|reply|respond|correspondence)\b',
        'blog_post': r'\b(blog post|blog|article|post|write about|content)\b',
        'linkedin': r'\b(linkedin|professional post|career update|networking)\b',
        'letter': r'\b(letter|formal letter|cover letter|business letter)\b',
        'essay': r'\b(essay|paper|write an essay|academic writing)\b',
        'report': r'\b(report|summary|analysis|write a report)\b',
        'social_media': r'\b(tweet|facebook post|instagram|social media)\b',
        'marketing': r'\b(marketing copy|advertisement|ad copy|promotional)\b',
        'proposal': r'\b(proposal|pitch|business proposal|project proposal)\b',
        'resume': r'\b(resume|cv|curriculum vitae|professional summary)\b',
        'story': r'\b(story|narrative|short story|creative writing)\b',
        'script': r'\b(script|screenplay|dialogue|conversation)\b'
    }
    
    # Common writing verbs
    writing_verbs = r'\b(write|draft|compose|create|craft|generate|help me write|can you write)\b'
    
    # Check for writing verbs first
    if not re.search(writing_verbs, prompt_lower):
        return False, ""
    
    # Check for specific writing types
    for writing_type, pattern in writing_patterns.items():
        if re.search(pattern, prompt_lower):
            return True, writing_type
    
    # Check for general writing indicators
    general_writing = r'\b(write|writing|written|draft|compose|content|copy)\b'
    if re.search(general_writing, prompt_lower):
        return True, "general"
    
    return False, ""

@mcp.tool()
def analyze_writing_request(prompt: str) -> str:
    """
    Analyze if a prompt contains a writing request and identify the type.
    
    Args:
        prompt: User prompt to analyze
        
    Returns:
        Analysis result with writing type if detected
    """
    try:
        is_writing, writing_type = detect_writing_request(prompt)
        
        if is_writing:
            return f"Writing request detected: {writing_type}"
        else:
            return "No writing request detected"
            
    except Exception as e:
        logger.error(f"Error analyzing writing request: {e}")
        return f"Error analyzing prompt: {str(e)}"

@mcp.tool()
def generate_content(
    content_type: str,
    request: str,
    tone: str = "professional",
    length: str = "medium",
    audience: str = "general"
) -> str:
    """
    Generate written content using GPT-4o-mini for various content types.
    
    Args:
        content_type: Type of content (email, blog_post, linkedin, etc.)
        request: Specific writing request/prompt
        tone: Tone for the content (professional, casual, formal, friendly)
        length: Length preference (short, medium, long)
        audience: Target audience (general, professional, technical, casual)
        
    Returns:
        Generated content or error message
    """
    try:
        if not openai_client:
            return "Error: OpenAI client not available. Please set OPENAI_API_KEY environment variable."
        
        # Create specialized prompts based on content type
        content_prompts = {
            'email': f"Write a {tone} email that {request}. Keep it {length} and appropriate for a {audience} audience.",
            'blog_post': f"Write a {tone} blog post about: {request}. Make it {length} length and engaging for a {audience} audience. Include a compelling introduction and conclusion.",
            'linkedin': f"Write a {tone} LinkedIn post about: {request}. Keep it {length} and professional, suitable for a {audience} professional network.",
            'letter': f"Write a {tone} formal letter that {request}. Make it {length} and appropriate for a {audience} recipient.",
            'essay': f"Write a {tone} essay about: {request}. Structure it with {length} length and clear arguments for a {audience} audience.",
            'report': f"Write a {tone} report on: {request}. Make it {length} with clear sections and suitable for a {audience} audience.",
            'social_media': f"Write a {tone} social media post about: {request}. Keep it {length} and engaging for a {audience} audience.",
            'marketing': f"Write {tone} marketing copy for: {request}. Make it {length} and compelling for a {audience} target audience.",
            'proposal': f"Write a {tone} proposal for: {request}. Structure it with {length} detail and persuasive content for a {audience} audience.",
            'resume': f"Write a {tone} resume section for: {request}. Make it {length} and professional for a {audience} industry.",
            'story': f"Write a {tone} story about: {request}. Make it {length} and engaging for a {audience} audience.",
            'script': f"Write a {tone} script for: {request}. Format it properly with {length} dialogue suitable for a {audience} audience.",
            'general': f"Write {tone} content for: {request}. Make it {length} and appropriate for a {audience} audience."
        }
        
        # Get the appropriate prompt or fall back to general
        system_prompt = content_prompts.get(content_type, content_prompts['general'])
        
        # Add length guidelines
        length_guidelines = {
            'short': "Keep it concise (100-200 words).",
            'medium': "Use moderate length (200-500 words).",
            'long': "Write in detail (500+ words)."
        }
        
        system_prompt += f" {length_guidelines.get(length, length_guidelines['medium'])}"
        
        # Call GPT-4o-mini
        logger.info(f"Generating {content_type} content with GPT-4o-mini")
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": f"You are a professional writing assistant. {system_prompt} Focus on clarity, engagement, and appropriate style."
                },
                {
                    "role": "user",
                    "content": request
                }
            ],
            max_tokens=1500,  # Reasonable limit for most content types
            temperature=0.7   # Balanced creativity and consistency
        )
        
        content = response.choices[0].message.content.strip()
        
        # Add metadata to response
        result = f"**Generated {content_type.replace('_', ' ').title()} ({tone} tone, {length} length)**\n\n"
        result += content
        result += f"\n\n*Generated using GPT-4o-mini for {audience} audience*"
        
        logger.info(f"Successfully generated {content_type} content ({len(content)} characters)")
        return result
        
    except Exception as e:
        error_msg = f"Error generating content: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
def smart_writing_assistant(prompt: str) -> str:
    """
    Intelligent writing assistant that automatically detects writing requests and generates appropriate content.
    
    Args:
        prompt: User's writing request
        
    Returns:
        Generated content based on detected writing type
    """
    try:
        # Detect writing type
        is_writing, writing_type = detect_writing_request(prompt)
        
        if not is_writing:
            return "This doesn't appear to be a writing request. For writing assistance, try phrases like 'write an email', 'draft a blog post', 'create a LinkedIn update', etc."
        
        # Auto-detect tone from prompt
        tone = "professional"  # default
        if any(word in prompt.lower() for word in ['casual', 'friendly', 'informal', 'relaxed']):
            tone = "casual"
        elif any(word in prompt.lower() for word in ['formal', 'official', 'business']):
            tone = "formal"
        elif any(word in prompt.lower() for word in ['creative', 'engaging', 'fun']):
            tone = "creative"
        
        # Auto-detect length preference
        length = "medium"  # default
        if any(word in prompt.lower() for word in ['short', 'brief', 'quick', 'concise']):
            length = "short"
        elif any(word in prompt.lower() for word in ['long', 'detailed', 'comprehensive', 'in-depth']):
            length = "long"
        
        # Auto-detect audience
        audience = "general"  # default
        if any(word in prompt.lower() for word in ['professional', 'business', 'corporate']):
            audience = "professional"
        elif any(word in prompt.lower() for word in ['technical', 'expert', 'specialist']):
            audience = "technical"
        elif any(word in prompt.lower() for word in ['casual', 'friends', 'personal']):
            audience = "casual"
        
        # Generate content
        return generate_content(
            content_type=writing_type,
            request=prompt,
            tone=tone,
            length=length,
            audience=audience
        )
        
    except Exception as e:
        error_msg = f"Error in writing assistant: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
def get_writing_templates() -> str:
    """
    Get templates and examples for different types of writing.
    
    Returns:
        List of available writing templates and examples
    """
    try:
        templates = {
            "Email Templates": [
                "Professional inquiry email",
                "Follow-up email after meeting",
                "Thank you email",
                "Complaint or feedback email",
                "Introduction email"
            ],
            "LinkedIn Posts": [
                "Career milestone announcement",
                "Industry insight sharing",
                "Professional achievement",
                "Networking post",
                "Thought leadership content"
            ],
            "Blog Post Ideas": [
                "How-to guide",
                "Industry analysis",
                "Personal experience story",
                "Product review",
                "Opinion piece"
            ],
            "Business Writing": [
                "Project proposal",
                "Status report",
                "Meeting summary",
                "Business letter",
                "Executive summary"
            ],
            "Marketing Content": [
                "Product description",
                "Social media caption",
                "Advertisement copy",
                "Newsletter content",
                "Landing page text"
            ]
        }
        
        result = "**Available Writing Templates and Examples:**\n\n"
        
        for category, items in templates.items():
            result += f"**{category}:**\n"
            for item in items:
                result += f"• {item}\n"
            result += "\n"
        
        result += "**Usage:** Ask me to write any of these types of content. For example:\n"
        result += "• 'Write a professional inquiry email about...'\n"
        result += "• 'Draft a LinkedIn post about my promotion'\n"
        result += "• 'Create a how-to blog post about...'\n"
        
        return result
        
    except Exception as e:
        error_msg = f"Error getting writing templates: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    mcp.run()