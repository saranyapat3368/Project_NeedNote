document.addEventListener('DOMContentLoaded', () => {
  // ยืนยันลบโน้ต
  document.querySelectorAll('.delete-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      if(!confirm('คุณแน่ใจหรือไม่ที่จะลบโน้ตนี้? การกระทำนี้ไม่สามารถย้อนกลับได้')) {
        e.preventDefault();
      }
    });
  });

  // กดใจ: toggle + อัปเดต UI ทันที
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-like]');
    if (!btn) return;

    const id = btn.getAttribute('data-like');
    const res = await fetch(`/note/${id}/like`, { method: 'POST' });
    const out = await res.json().catch(() => ({ ok: false }));
    if (!out.ok) return;

    // อัปเดตสถานะ/ตัวเลข/ไอคอน
    const likedNow = !!out.liked;
    btn.setAttribute('data-liked', likedNow ? '1' : '0');

    const countSpan = btn.querySelector('.like-count');
    if (countSpan) countSpan.textContent = out.count;

    btn.textContent = ''; // เคลียร์
    btn.insertAdjacentHTML('afterbegin',
      `${likedNow ? '❤️' : '🤍'} ใจ (<span class="like-count">${out.count}</span>)`
    );
  });

  // รายงานโน้ต
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-report]');
    if (!btn) return;
    const id = btn.getAttribute('data-report');
    if (!confirm('ยืนยันรายงานโน้ตนี้หรือไม่?')) return;
    await fetch(`/note/${id}/report`, { method: 'POST' });
    alert('ส่งรายงานแล้ว ขอบคุณค่ะ');
  });

  // รายงานคอมเมนต์
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-report-comment]');
    if (!btn) return;
    const cid = btn.getAttribute('data-report-comment');
    const nid = btn.getAttribute('data-note');
    if (!confirm('รายงานคอมเมนต์นี้?')) return;
    await fetch(`/comment/${nid}/${cid}/report`, { method: 'POST' });
    alert('ส่งรายงานคอมเมนต์แล้ว');
  });

  // ลบคอมเมนต์ของฉัน
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-del-comment]');
    if (!btn) return;
    const cid = btn.getAttribute('data-del-comment');
    const nid = btn.getAttribute('data-note');
    if (!confirm('ลบคอมเมนต์ของคุณ?')) return;
    const res = await fetch(`/comment/${nid}/${cid}/delete`, { method: 'POST' });
    const out = await res.json().catch(() => ({ ok: false }));
    if (out.ok) location.reload();
  });
});
