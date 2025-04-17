import os
import httpx

GITLAB_API_URL = "https://gitlab.com/api/v4"
TOKEN = os.getenv("GITLAB_TOKEN")


async def get_merge_request_changes(project_id, mr_iid):
    url = f"{GITLAB_API_URL}/projects/{project_id}/merge_requests/{mr_iid}/changes"
    headers = {"PRIVATE-TOKEN": TOKEN}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        return res.json()


async def post_mr_comment(project_id, mr_iid, body):
    url = f"{GITLAB_API_URL}/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": TOKEN}
    data = {"body": body}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, data=data)
