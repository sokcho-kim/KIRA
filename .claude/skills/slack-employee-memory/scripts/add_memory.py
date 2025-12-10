#!/usr/bin/env python3
"""
Add new information to memory with automatic classification.
Handles various content types: Slack messages, Confluence docs, emails, etc.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class MemoryManager:
    """Manage employee memory with automatic classification."""
    
    CONTENT_TYPES = {
        'channel': 'channels',
        'user': 'users',
        'project': 'projects',
        'decision': 'decisions',
        'task': 'tasks',
        'meeting': 'meetings',
        'feedback': 'feedback',
        'announcement': 'announcements',
        'resource': 'resources',
        'news': 'external/news',
        'misc': 'misc'
    }
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
    
    def classify_content(self, content: str, metadata: Dict) -> str:
        """
        Automatically classify content based on metadata and content analysis.
        Returns the target directory name.
        """
        # Check explicit type in metadata
        if 'type' in metadata:
            content_type = metadata['type'].lower()
            if content_type in self.CONTENT_TYPES:
                return self.CONTENT_TYPES[content_type]
        
        # Auto-classify based on keywords and metadata
        content_lower = content.lower()
        
        # Channel-related
        if any(key in metadata for key in ['channel_id', 'channel_name', 'slack_channel']):
            return 'channels'
        
        # User-related
        if any(key in metadata for key in ['user_id', 'user_name', 'user_profile']):
            return 'users'
        
        # Project-related keywords
        project_keywords = ['프로젝트', 'project', '진행상황', 'milestone', '로드맵', 'roadmap']
        if any(keyword in content_lower for keyword in project_keywords):
            return 'projects'
        
        # Decision-related keywords
        decision_keywords = ['결정', 'decision', '승인', 'approval', '합의', 'agreement']
        if any(keyword in content_lower for keyword in decision_keywords):
            return 'decisions'
        
        # Task-related keywords
        task_keywords = ['업무', 'task', '완료', 'completed', '수행', 'action item']
        if any(keyword in content_lower for keyword in task_keywords):
            return 'tasks'
        
        # Meeting-related keywords
        meeting_keywords = ['회의', 'meeting', '미팅', '논의', 'discussion']
        if any(keyword in content_lower for keyword in meeting_keywords):
            return 'meetings'
        
        # Feedback-related keywords
        feedback_keywords = ['피드백', 'feedback', '개선', 'improvement', '제안', 'suggestion']
        if any(keyword in content_lower for keyword in feedback_keywords):
            return 'feedback'
        
        # Announcement-related keywords
        announcement_keywords = ['공지', 'announcement', '알림', 'notice']
        if any(keyword in content_lower for keyword in announcement_keywords):
            return 'announcements'
        
        # News/external keywords
        news_keywords = ['뉴스', 'news', '기사', 'article', '외부', 'external']
        if any(keyword in content_lower for keyword in news_keywords):
            return 'external/news'
        
        # Default to misc
        return 'misc'
    
    def generate_filename(self, title: str, metadata: Dict) -> str:
        """Generate a clean filename from title."""
        # Use provided filename if exists
        if 'filename' in metadata:
            return metadata['filename']
        
        # Clean title for filename
        clean_title = title.strip()
        # Remove special characters
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            clean_title = clean_title.replace(char, '')
        
        # Truncate if too long
        if len(clean_title) > 50:
            clean_title = clean_title[:50]
        
        # Add date prefix if specified
        if metadata.get('add_date_prefix', False):
            date_prefix = datetime.now().strftime('%Y%m%d')
            clean_title = f"{date_prefix}_{clean_title}"
        
        return f"{clean_title}.md"
    
    def format_metadata(self, metadata: Dict) -> str:
        """Format metadata as YAML frontmatter."""
        lines = ["---"]
        
        # Add created timestamp
        if 'created' not in metadata:
            metadata['created'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for key, value in metadata.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                # Escape special characters in strings
                if isinstance(value, str) and any(c in value for c in [':', '#', '-']):
                    value = f'"{value}"'
                lines.append(f"{key}: {value}")
        
        lines.append("---")
        return '\n'.join(lines)
    
    def add_memory(self, title: str, content: str, metadata: Optional[Dict] = None) -> Tuple[str, str]:
        """
        Add new memory entry.
        Returns (directory, filename) of created file.
        """
        if metadata is None:
            metadata = {}
        
        # Classify content
        target_dir = self.classify_content(content, metadata)
        
        # Add classification to metadata
        metadata['category'] = target_dir
        
        # Generate filename
        filename = self.generate_filename(title, metadata)
        
        # Create full path
        dir_path = self.base_path / target_dir
        file_path = dir_path / filename

        # Check if this is a profile file (channels/ or users/)
        is_profile_file = target_dir in ['channels', 'users']

        # Handle existing file
        if file_path.exists():
            if is_profile_file:
                # Profile files should be updated, not versioned
                print(f"📝 Updating existing profile: {target_dir}/{filename}")
                self.update_memory(target_dir, filename, content, metadata)
                return target_dir, filename
            else:
                # Topic files can be versioned if same name exists
                base_name = file_path.stem
                counter = 1
                while file_path.exists():
                    filename = f"{base_name}_v{counter}.md"
                    file_path = dir_path / filename
                    counter += 1

        # Format full content
        full_content = f"{self.format_metadata(metadata)}\n\n# {title}\n\n{content}"

        # Write file
        file_path.write_text(full_content, encoding='utf-8')

        print(f"✅ Memory added: {target_dir}/{filename}")
        return target_dir, filename
    
    def update_memory(self, directory: str, filename: str, new_content: str, 
                      new_metadata: Optional[Dict] = None) -> None:
        """Update existing memory entry."""
        file_path = self.base_path / directory / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Memory file not found: {directory}/{filename}")
        
        # Read existing file
        existing_content = file_path.read_text(encoding='utf-8')
        
        # Extract existing metadata
        if existing_content.startswith('---'):
            parts = existing_content.split('---', 2)
            if len(parts) >= 3:
                # Parse and update metadata
                import yaml
                try:
                    existing_metadata = yaml.safe_load(parts[1])
                except:
                    existing_metadata = {}
                
                if new_metadata:
                    existing_metadata.update(new_metadata)
                
                # Add update timestamp
                existing_metadata['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Reconstruct file
                full_content = f"{self.format_metadata(existing_metadata)}\n\n{new_content}"
                file_path.write_text(full_content, encoding='utf-8')
                
                print(f"✅ Memory updated: {directory}/{filename}")
                return
        
        # If no metadata found, just update content
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✅ Memory updated: {directory}/{filename}")

def main():
    """Main CLI interface."""
    if len(sys.argv) < 4:
        print("Usage: python add_memory.py <memory_path> <title> <content> [metadata_json]")
        print("\nExample:")
        print('  python add_memory.py /memory "마케팅 채널 가이드" "..." \'{"type":"channel"}\'')
        sys.exit(1)
    
    memory_path = sys.argv[1]
    title = sys.argv[2]
    content = sys.argv[3]
    
    metadata = {}
    if len(sys.argv) > 4:
        try:
            metadata = json.loads(sys.argv[4])
        except json.JSONDecodeError:
            print("Warning: Invalid JSON metadata, using empty metadata")
    
    manager = MemoryManager(memory_path)
    directory, filename = manager.add_memory(title, content, metadata)
    
    print(f"\n📍 Location: {directory}/{filename}")

if __name__ == "__main__":
    main()
