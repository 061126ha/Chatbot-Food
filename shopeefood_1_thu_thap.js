
// khởi tạo bộ nhớ: 1 ngăn chứa quán, 1 ngăn chứa URL dã quét
(() => {
    const STORAGE_ROWS_KEY = 'mergedFoodRowsByDistrict';
    const STORAGE_URLS_KEY = 'scrapedShopUrlsByDistrict';

    if (!localStorage.getItem(STORAGE_ROWS_KEY)) {
        localStorage.setItem(STORAGE_ROWS_KEY, JSON.stringify([]));
    }
    if (!localStorage.getItem(STORAGE_URLS_KEY)) {
        localStorage.setItem(STORAGE_URLS_KEY, JSON.stringify([]));
    }
//Danh sách các quận
    const DISTRICTS = [
        'Ba Đình', 'Bắc Từ Liêm', 'Cầu Giấy', 'Đống Đa', 'Hà Đông',
        'Hai Bà Trưng', 'Hoàn Kiếm', 'Hoàng Mai', 'Long Biên',
        'Nam Từ Liêm', 'Tây Hồ', 'Thanh Trì', 'Thanh Xuân',
        'Gia Lâm', 'Đông Anh', 'Sóc Sơn', 'Mê Linh', 'Chương Mỹ',
        'Thanh Oai', 'Thường Tín', 'Phú Xuyên', 'Ứng Hòa', 'Mỹ Đức',
        'Đan Phượng', 'Hoài Đức', 'Quốc Oai', 'Thạch Thất', 'Phúc Thọ',
        'Ba Vì', 'Sơn Tây'
    ];
//Rút quận từ địa chỉ
    function extractDistrict(addrText) {
        //Tìm tên quận trong từ điển
        const cleanAddr = (addrText || '').replace(/\s+/g, ' ').trim();
        for (const d of DISTRICTS) {
            const regex = new RegExp(`(^|[,\\-–]\\s*)(Q\\.?\\s*|H\\.?\\s*|Quận\\s*|Huyện\\s*)?${d}(?=$|[,\\-–])`, 'i');
            if (regex.test(cleanAddr)) {
                return d;
            }
        }
        //lấy phần tử áp chót khi tách theo dấu phẩy
        const parts = cleanAddr.split(',').map(p => p.trim()).filter(Boolean);
        if (parts.length >= 2) {
            const candidate = parts[parts.length - 2]
                .replace(/^(Quận|Huyện|Q\.|H\.)\s+/i, '')
                .trim();
            if (candidate) return candidate;
        }
         // Cách 3: mặc định
        return 'Khác';
    }
// chuẩn hoá giá về dạng 45.00đ or vnd
    function normalizePriceText(raw) {
        if (!raw) return '';
        const matches = raw.match(/\d[\d.,]*\s*(đ|vnd)?/gi);
        if (!matches || matches.length === 0) return raw.replace(/\s+/g, ' ').trim();
        let val = matches[0].trim();
        if (!/đ$/i.test(val)) {
            val = val.replace(/[^\d.,]/g, '') + 'đ';
        }
        return val.replace(/\s+/g, '');
    }
//Tách giá gốc và giá khuyến mãi
    function extractPrices(itemEl, priceEl) {
        const oldPriceEl = itemEl.querySelector(
            '.old-price, .price-old, .original-price, [class*="old-price"], [class*="line-through"], del, s'
        );
        const promoEl = itemEl.querySelector(
            '.discount-price, .promo-price, .current-price, [class*="discount"], [class*="promo"]'
        );

        let price = '';
        let promoPrice = '';
// Nhánh A: có giá cũ gạch ngang
        if (oldPriceEl && priceEl) {
            const p1 = normalizePriceText(oldPriceEl.innerText);
            const p2 = normalizePriceText(priceEl.innerText);
            if (p1 && p2 && p1 !== p2) {
                price = p1;
                promoPrice = p2;
            } else {
                price = p2 || p1;
            }
        } 
          // Nhánh B: có phần tử khuyến mãi riêng
        else if (promoEl && priceEl) {
            const p1 = normalizePriceText(priceEl.innerText);
            const p2 = normalizePriceText(promoEl.innerText);
            if (p1 && p2 && p1 !== p2) {
                price = p1;
                promoPrice = p2;
            } else {
                price = p1 || p2;
            }
             // Nhánh C: dự phòng, đọc cả khối text
        } else {
            const rawText = priceEl ? priceEl.innerText : '';
            const allPrices = [...rawText.matchAll(/\d[\d.,]*\s*đ/gi)].map(m => m[0].replace(/\s+/g, ''));
            if (allPrices.length >= 2) {
                promoPrice = allPrices[0];
                price = allPrices[1];
            } else if (allPrices.length === 1) {
                price = allPrices[0];
            } else {
                price = normalizePriceText(rawText);
            }
        }

        return { price, promoPrice };
    }
//lấy địa chỉ và quận
    let address = document.title ? document.title.replace(/\s*-\s*ShopeeFood.*$/i, '').trim() : 'Đang cập nhật';
    const addressMeta = document.querySelector('.address, .restaurant-detail__address, [class*="address"]');
    if (addressMeta && addressMeta.innerText.trim()) {
        address = addressMeta.innerText.replace(/\s+/g, ' ').trim();
    }
    const district = extractDistrict(address);
//Chống trùng và quét món lấy từ mảng ocalStorage, push thêm, ghi ngược lại
    const shopUrls = JSON.parse(localStorage.getItem(STORAGE_URLS_KEY));
    const currentUrl = window.location.href;

    if (!shopUrls.includes(currentUrl)) {
        shopUrls.push(currentUrl);
        localStorage.setItem(STORAGE_URLS_KEY, JSON.stringify(shopUrls));

        const currentRows = JSON.parse(localStorage.getItem(STORAGE_ROWS_KEY));
        let count = 0;

        const dishItems = document.querySelectorAll('.menu-item-content, .item-restaurant-row, .dish-item, [class*="dish-item"]');

        dishItems.forEach((item) => {
            const nameEl = item.querySelector('.item-name, .dish-name, [class*="name"]');
            const priceEl = item.querySelector('.price, .item-price, [class*="price"]');

            const name = nameEl ? nameEl.innerText.replace(/\s+/g, ' ').trim() : '';
            const { price, promoPrice } = extractPrices(item, priceEl);

            if (name) {
                currentRows.push({
                    district,
                    name,
                    price,
                    promoPrice,
                    address
                });
                count++;
            }
        });

        localStorage.setItem(STORAGE_ROWS_KEY, JSON.stringify(currentRows));
        console.log(`Đã lưu thêm ${count} món (${district}) từ quán này! Tổng số món hiện tại: ${currentRows.length}`);
    } else {
        console.log('Quán này đã được quét trước đó rồi.');
    }
})();
