# Memory System

KIRA automatically remembers and utilizes important information.

## 🧠 Memory Structure

### Local File System
All memory is stored as Markdown files on your computer.

```
~/Documents/KIRA/memories/
├── channels/          # Per-channel conversation history
├── projects/          # Project information
├── users/            # Per-user information
├── decisions/        # Important decisions
└── index.md          # Auto-generated index
```

---

## 👤 Per-User Memory

### Personal Preferences
KIRA recognizes each user individually and remembers preferences.

### Per-User Work History
Manages each user's work history separately.

---

## 🤝 Context Sharing

### Team Collaboration Scenario
Everyone shares conversation context from channel discussions.

---

## 📚 Auto Save

### Auto Save During Conversation
Important information is automatically saved to memory during conversations.

**Auto-saved information:**
- Project-related discussions
- Important decisions
- User preferences
- Task assignments and schedules

---

## 🔍 Intelligent Search

### Auto-Reference During Task Execution
KIRA automatically finds and uses relevant memory when performing tasks.

```
User: Send status update email to project lead

KIRA: [Auto-search memory]
      - Project: Project Alpha
      - Lead: Bob Lee (bob@company.com)
      - Current status: Development phase

      Drafting status update email to Bob...
```

---

## 🔐 Data Security

### Local Storage
- All memory stored only on your computer
- Not transmitted to external servers
- Stored as files for easy backup and transfer

---

## 🚀 Memory Initialization Guide

Building memory systematically when first using KIRA makes it much more effective.

### Step 1: Save Team Member Info
Tag team members in a channel and KIRA auto-collects info:

```
User: @KIRA Remember our team members
      @John Doe @Jane Smith @Bob Lee

KIRA: [Collect info via Slack MCP]
      - Name, email, Slack ID
      - Profile photo, title (if available)

      Remembered 3 team members!
```

**Later usage:**
```
User: Send email to John

KIRA: [Auto-recognize from memory]
      I'll send email to john@company.com.
      What's the content?
```

### Step 2: Teach Organization Structure
Explain your organization structure and roles:

```
User: KIRA, remember our org structure
      - CEO: John Doe (john@company.com)
      - CTO: Jane Smith (jane@company.com)
      - Dev Lead: Bob Lee (bob@company.com)
      - I'm on the dev team

KIRA: Got it! I've recorded the org structure.
      [Saved to memory]
```

### Step 3: Share Project Info
Tell KIRA about ongoing projects:

```
User: KIRA, we're working on "Project Alpha"
      Team: Me and Bob
      Period: 2025-01-01 ~ 2025-03-31
      Goal: New feature development

KIRA: Recorded Project Alpha info!
```

### Step 4: Remember Confluence Docs
Share links and ask to remember important documents:

```
User: KIRA, read and remember this Confluence doc
      https://confluence.company.com/display/TEAM/API-Guidelines

KIRA: [Read doc via Confluence MCP]
      Read and saved API guidelines doc to memory.

      Key points:
      - REST API principles
      - Naming conventions
      - Error handling methods
      ...
```

::: tip Benefits of Building Memory
Building memory early enables:
- Recognize people without tagging
- "Send email to John" → auto-recognize email address
- Auto-reference project context
- Use info instantly without searching docs
:::

---

## 🛠️ Memory Management

### Edit Memory
Fix incorrect or changed information:

```
User: KIRA, update John's email
      Old: john@company.com
      New: john.doe@newcompany.com

KIRA: Updated John Doe's email address.
      john@company.com → john.doe@newcompany.com
```

### Delete Memory
Remove unnecessary information:

```
User: KIRA, Bob left the company. Remove from memory

KIRA: Removed Bob Lee's info from memory.
```

### Query Memory
Check stored information:

```
User: KIRA, tell me about Project Alpha

KIRA: [Memory search]
      Project Alpha:
      - Team: You, Bob
      - Period: 2025-01-01 ~ 2025-03-31
      - Goal: New feature development
      - Status: In progress
```

---

## ❓ Next Steps

- [Chat](/features/chat) - Effective communication
- [Task Execution](/features/tasks) - Tasks using memory
- [Proactive Suggestions](/features/proactive) - Memory-based auto suggestions
