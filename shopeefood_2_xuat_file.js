//Xuất file
//Phân tích: rawData ? JSON.parse(rawData) : [] tránh lỗi khi chưa có dữ liệu. 
// return thoát sớm (early return) giúp phần sau không cần lồng thêm if.
    
(() => {
    const STORAGE_ROWS_KEY = 'mergedFoodRowsByDistrict';
    const rawData = localStorage.getItem(STORAGE_ROWS_KEY);
    const rows = rawData ? JSON.parse(rawData) : [];

    if (!rows.length) {
        console.log('Chưa có dữ liệu nào được ghi nhận.');
        return;
    }
//Map gom nhóm: khóa là quận, giá trị là mảng món. Quận chưa có thì tạo mảng rỗng rồi mới push.
const grouped = new Map();
    for (const row of rows) {
        const district = (row.district || 'Khác').trim();
        if (!grouped.has(district)) {
            grouped.set(district, []);
        }
        grouped.get(district).push({
            name: (row.name || '').trim(),
            price: (row.price || '').trim(),
            promoPrice: (row.promoPrice || '').trim(),
            address: (row.address || '').trim()
        });
    }
//Dựng nội dung theo kiểu "mảng các dòng": mỗi phần tử là một dòng, cuối cùng nối bằng \n. Cách này dễ đọc và dễ sửa hơn cộng chuỗi dài.
    const sortedDistricts = [...grouped.keys()].sort((a, b) =>
        a.localeCompare(b, 'vi', { sensitivity: 'base' })
    );

    const totalItems = rows.length;
    const totalDistricts = sortedDistricts.length;

    const lines = [
        '# Danh sách món ăn theo quận/huyện – Hà Nội',
        '',
        `Tổng số món: ${totalItems} | Số quận/huyện: ${totalDistricts}`,
        '',
        '## Mục lục',
        ''
    ];

    for (const d of sortedDistricts) {
        lines.push(`- ${d} (${grouped.get(d).length} món)`);
    }

    lines.push('', '---', '');

    let currentId = 1;
    for (const d of sortedDistricts) {
        lines.push(`# ${d}`, '');

        for (const item of grouped.get(d)) {
            lines.push(`ID: ${currentId}`);
            lines.push(`Tên món: ${item.name}`);
            lines.push(`Giá: ${item.price}`);
            if (item.promoPrice) {
                lines.push(`Giá khuyến mãi: ${item.promoPrice}`);
            }
            lines.push(`Địa chỉ: ${item.address}`);
            lines.push('', '---', '');
            currentId++;
        }
    }

    const finalContent = lines.join('\n').trimEnd() + '\n';
    const blob = new Blob([finalContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data_food_theo_quan.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log(`Đã xuất thành công file 'data_food_theo_quan.md' (${totalItems} món, ${totalDistricts} quận/huyện)!`);
})();
