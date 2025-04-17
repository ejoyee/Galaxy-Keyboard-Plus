from gitlab_api import get_merge_request_changes, post_mr_comment
from llm import generate_review_prompt


def summarize_changes(changes):
    summary = ""
    for change in changes.get("changes", []):
        summary += f"- {change['new_path']}: +{len(change['diff'].splitlines())} lines changed\n"
    return summary


async def handle_merge_request(event):
    project_id = event["project"]["id"]
    mr_iid = event["object_attributes"]["iid"]
    mr_desc = event["object_attributes"].get("description", "")

    changes = await get_merge_request_changes(project_id, mr_iid)
    changes_summary = summarize_changes(changes)

    review = await generate_review_prompt(mr_desc, changes_summary)
    await post_mr_comment(project_id, mr_iid, f"🤖 자동 코드 리뷰 결과:\n\n{review}")
