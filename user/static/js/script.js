// รอให้หน้าเว็บโหลดเสร็จทั้งหมดก่อน
document.addEventListener('DOMContentLoaded', () => {

    // หาฟอร์มลบทั้งหมดในหน้าที่มี class "delete-form"
    const deleteForms = document.querySelectorAll('.delete-form');

    // ใส่ฟังก์ชัน "เมื่อถูกส่ง" ให้กับทุกฟอร์ม
    deleteForms.forEach(form => {
        form.addEventListener('submit', (event) => {
            // แสดงกล่องข้อความยืนยัน
            const confirmation = confirm('คุณแน่ใจหรือไม่ที่จะลบโน้ตนี้? การกระทำนี้ไม่สามารถย้อนกลับได้');
            
            // ถ้าผู้ใช้กด "Cancel" (ยกเลิก)
            if (!confirmation) {
                event.preventDefault(); // ให้ยกเลิกการส่งฟอร์ม (ไม่ลบ)
            }
        });
    });

});
