# Demo Proposal Project

## Scenario

A client has requested an "AI product launch campaign" but the requirements are vague. 

This demo shows how to use Framing Ledger to:
1. Initialize a project
2. Frame the problem
3. Close out a session

## How to Use

```bash
# 1. Initialize the project
cd demo-proposal-project
flg init "AI Product Launch Campaign" --type proposal --client "TechCorp"

# 2. Check framing completeness
flg frame

# 3. Review the generated patch and update FRAMING.md

# 4. Close out a session
flg closeout --transcript demo_transcript.md
```

## Expected Output

After running the commands, you should see:
- Standard FLG project structure created
- Frame patch identifying missing fields
- Closeout patch with extracted decisions, risks, and progress
