from gitlab_api import get_merge_request_changes, post_mr_comment
from llm import generate_review_prompt_chunked


def summarize_changes(changes):
    summary = ""
    for change in changes.get("changes", []):
        filename = change.get("new_path", "unknown")
        diff = change.get("diff", "")

        summary += f"📄 {filename} 변경사항:\n"
        summary += diff + "\n" + ("-" * 40) + "\n"
    return summary


async def handle_merge_request(event):
    print("📥 [Handler] Merge Request 이벤트 처리 시작")
    project_id = event["project"]["id"]
    mr_iid = event["object_attributes"]["iid"]
    mr_desc = event["object_attributes"].get("description", "")

    print(f"🔎 [Handler] project_id={project_id}, mr_iid={mr_iid}")
    print("📦 [Handler] MR 설명:", mr_desc)

    changes = await get_merge_request_changes(project_id, mr_iid)
    changes_summary = summarize_changes(changes)

    print("📊 [Handler] 변경 요약 (총 길이:", len(changes_summary), "자)")
    review = await generate_review_prompt_chunked(mr_desc, changes_summary)

    print("✍️ [Handler] GPT 리뷰 결과:")
    print(review)

    await post_mr_comment(project_id, mr_iid, f"🤖 자동 코드 리뷰 결과:\n\n{review}")
    print("🎉 [Handler] 코드 리뷰 완료 및 댓글 등록")
