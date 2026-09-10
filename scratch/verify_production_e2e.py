import urllib.request
import json
import time

BASE_URL = 'http://127.0.0.1:8000'

print('=== 1. VERIFY HEALTH ENDPOINT ===')
req = urllib.request.Request(f'{BASE_URL}/api/health')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print('Health response:', data)
    assert resp.status == 200
    assert data.get('status') == 'healthy' or data.get('success') is True

print('\n=== 2. VERIFY FEATURE 1: METADATA EXPORT (COLD & WARM CACHE) ===')
for run_num, label in [(1, 'COLD CACHE'), (2, 'WARM CACHE')]:
    print(f'\n--- Starting Run {run_num}: {label} ---')
    post_data = json.dumps({'channel': 'JEEAasaanHai', 'limit': 0}).encode('utf-8')
    req = urllib.request.Request(
        f'{BASE_URL}/api/export',
        data=post_data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        job_info = json.loads(resp.read().decode())
        job_id = job_info['job_id']
        print(f'Created job: {job_id}')

    max_wait = 60
    start_t = time.time()
    completed = False
    progress_data = {}
    while time.time() - start_t < max_wait:
        req = urllib.request.Request(f'{BASE_URL}/api/export/{job_id}/progress')
        with urllib.request.urlopen(req) as resp:
            progress_data = json.loads(resp.read().decode())
            status = progress_data.get('status')
            if status == 'completed':
                completed = True
                break
            elif status == 'failed':
                raise RuntimeError(f'Job failed: {progress_data}')
        time.sleep(1)

    assert completed, f'Job did not complete within {max_wait}s'
    elapsed = time.time() - start_t
    print(f'Run {run_num} completed in {elapsed:.2f}s!')

    req = urllib.request.Request(f'{BASE_URL}/api/export/{job_id}/result')
    with urllib.request.urlopen(req) as resp:
        result_data = json.loads(resp.read().decode())
        res = result_data.get('result', {})
        total_videos = res.get('total_videos', 0)
        total_discovered = res.get('total_discovered', 0)
        print(f'Result: channel="{res.get("channel_title")}", total_discovered={total_discovered}, total_videos={total_videos}')
        assert total_videos > 0, f'Expected total_videos > 0, got {total_videos}!'

    download_url = f'{BASE_URL}/api/export/{job_id}/download'
    req = urllib.request.Request(download_url)
    with urllib.request.urlopen(req) as resp:
        csv_bytes = resp.read()
        csv_text = csv_bytes.decode('utf-8')
        lines = [l for l in csv_text.splitlines() if l.strip()]
        header = lines[0]
        data_rows = len(lines) - 1
        print(f'CSV Header: {header}')
        print(f'CSV Rows Count: {data_rows}')
        assert data_rows == total_videos, f'CSV rows {data_rows} != total_videos {total_videos}'
        print(f'First data row preview: {lines[1][:100]}...')


print('\n=== 3. VERIFY FEATURE 2: URL -> TRANSCRIPT ===')
test_vid = 'nKjSR0H8UT4'
req = urllib.request.Request(f'{BASE_URL}/api/transcriptv2/{test_vid}')
with urllib.request.urlopen(req) as resp:
    t_data = json.loads(resp.read().decode())
    print('Transcript Video ID:', t_data.get('video_id'))
    print('Title:', t_data.get('title'))
    print('Duration:', t_data.get('duration'))
    print('Status:', t_data.get('status'))
    print('Method:', t_data.get('method'))
    transcript_snippet = t_data.get('transcript', '')[:200]
    print('Transcript preview (first 200 chars):', transcript_snippet)
    assert t_data.get('status') == 'success'
    assert len(t_data.get('transcript', '')) > 50

print('\nALL LIVE END-TO-END VERIFICATIONS PASSED!')