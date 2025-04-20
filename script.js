// مدیریت سبد خرید
let cart = JSON.parse(localStorage.getItem('cart')) || [];

function updateCartCounter() {
    document.getElementById('cart-counter').textContent = cart.length;
}

function addToCart(productName, price) {
    cart.push({name: productName, price: price});
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCounter();
    alert(`${productName} به سبد اضافه شد!`);
}

// اسکرول نرم
function scrollToProducts() {
    document.querySelector('#products').scrollIntoView({
        behavior: 'smooth'
    });
}

// ارسال فرم
function submitForm(e) {
    e.preventDefault();
    alert('پیام شما با موفقیت ارسال شد!');
    e.target.reset();
}

// بارگذاری اولیه
document.addEventListener('DOMContentLoaded', () => {
    updateCartCounter();
});
