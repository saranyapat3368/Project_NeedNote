document.addEventListener('DOMContentLoaded', () => {

    // --- ส่วนนี้คือการทำให้ปุ่มเมนู (Dashboard, Users, Reports) กดแล้วสลับหน้าได้ ---

    // 1. ค้นหาและเก็บปุ่มเมนูทั้งหมดและหน้าเนื้อหาทั้งหมดไว้ในตัวแปร
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page');

    // 2. วนลูปเพื่อใส่ฟังก์ชัน "เมื่อถูกคลิก" (Event Listener) ให้กับทุกปุ่ม
    navLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            
            // ป้องกันไม่ให้หน้าเว็บรีโหลดเมื่อคลิกที่ลิงก์
            event.preventDefault(); 

            // หา ID ของหน้าที่เราต้องการจะเปิด จาก thuộc tính 'data-page' ของปุ่มที่ถูกคลิก
            // เช่น ถ้าคลิกปุ่ม <a data-page="users">...</a> ก็จะได้ 'users'
            const pageId = link.getAttribute('data-page');
            const targetPage = document.getElementById(pageId + '-page');

            // 3. ซ่อนทุกหน้า และเอาไฮไลท์ (คลาส .active) ออกจากทุกปุ่ม
            pages.forEach(page => {
                page.classList.remove('active');
            });
            navLinks.forEach(nav => {
                nav.classList.remove('active');
            });

            // 4. แสดงเฉพาะหน้าที่ต้องการ (targetPage) และไฮไลท์เฉพาะปุ่มที่ถูกคลิก
            if (targetPage) {
                targetPage.classList.add('active');
            }
            link.classList.add('active');
        });
    });

    // คุณสามารถเพิ่มโค้ดสำหรับปุ่มอื่นๆ (เช่น ปุ่ม hamburger menu) ได้ที่นี่
    // const menuBtn = document.getElementById('menu-btn');
    // menuBtn.addEventListener('click', () => { ... });

});

