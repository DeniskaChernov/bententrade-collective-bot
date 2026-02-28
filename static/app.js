const tg = window.Telegram?.WebApp;
const userId = tg?.initDataUnsafe?.user?.id?.toString() || "guest";

let colors = [];
let cart = JSON.parse(localStorage.getItem("cart")) || [];

// ---------------- UTIL ----------------

function saveCart() {
    localStorage.setItem("cart", JSON.stringify(cart));
    updateCartBar();
}

function updateCartBar() {
    const totalKg = cart.reduce((sum, item) => sum + item.weight, 0);
    document.getElementById("cartTotalKg").innerText = totalKg;

    const bar = document.getElementById("cartBar");
    totalKg > 0 ? bar.classList.remove("hidden") : bar.classList.add("hidden");
}

// ---------------- COUNTDOWN ----------------

function formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}ч ${m}м ${s}с`;
}

// ---------------- LOAD COLORS ----------------

async function loadColors() {
    const res = await fetch(`/api/colors?user_id=${userId}`);
    colors = await res.json();
    renderColors();
}

function renderColors() {
    const container = document.getElementById("colorsContainer");
    container.innerHTML = "";

    if (colors.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>Активных партий пока нет</h3>
                <p>Посмотрите каталог доступных цветов ниже</p>
            </div>
        `;
        return;
    }

    colors.forEach(color => {

        const percent = Math.min(
            (color.total_weight / color.min_weight) * 100,
            100
        );

        const glow = color.total_weight >= color.min_weight ? "glow" : "";

        let countdownHtml = "";
        if (color.status === "waiting_24h" && color.remaining_seconds > 0) {
            countdownHtml = `
                <div class="countdown">
                    Закрытие через:
                    <span id="timer-${color.id}">
                        ${formatTime(color.remaining_seconds)}
                    </span>
                </div>
            `;
        }

        let buttonHtml = "";

        if (color.status === "closed") {
            buttonHtml = `
                <div class="status-text">
                    Производство запущено
                </div>
            `;
        } else {
            buttonHtml = `
                <button class="button"
                        onclick="addToCart(${color.id})">
                    +5 кг
                </button>
            `;
        }

        container.innerHTML += `
            <div class="card ${glow}">
                <div class="card-image">
                    <img src="${color.image_url || '/static/images/placeholder.jpg'}">
                </div>

                <div class="card-content">
                    <div class="card-title">
                        ${color.article} — ${color.name}
                    </div>

                    <div class="card-sub">
                        ${color.format}
                    </div>

                    <div class="progress">
                        <div class="progress-fill"
                             style="width:${percent}%">
                        </div>
                    </div>

                    <div class="card-sub">
                        Собрано ${color.total_weight} / ${color.min_weight} кг
                    </div>

                    ${color.user_weight > 0 ? `
                        <div class="user-contribution">
                            Ваш вклад: ${color.user_weight} кг
                        </div>
                    ` : ""}

                    ${countdownHtml}

                    ${buttonHtml}
                </div>
            </div>
        `;
    });

    startCountdowns();
}

// ---------------- COUNTDOWN LIVE UPDATE ----------------

function startCountdowns() {
    colors.forEach(color => {
        if (color.status === "waiting_24h" && color.remaining_seconds > 0) {

            const interval = setInterval(() => {

                color.remaining_seconds--;

                const el = document.getElementById(`timer-${color.id}`);
                if (el && color.remaining_seconds >= 0) {
                    el.innerText = formatTime(color.remaining_seconds);
                }

                if (color.remaining_seconds <= 0) {
                    clearInterval(interval);
                    loadColors();
                }

            }, 1000);
        }
    });
}

// ---------------- CART LOGIC ----------------

function addToCart(colorId) {
    const existing = cart.find(i => i.color_id === colorId);

    if (existing) {
        existing.weight += 5;
    } else {
        cart.push({
            color_id: colorId,
            weight: 5
        });
    }

    saveCart();
}

function removeFromCart(index) {
    cart.splice(index, 1);
    saveCart();
    renderCart();
}

function increaseWeight(index) {
    cart[index].weight += 5;
    saveCart();
    renderCart();
}

function decreaseWeight(index) {
    cart[index].weight -= 5;
    if (cart[index].weight <= 0) cart.splice(index, 1);
    saveCart();
    renderCart();
}

// ---------------- CART MODAL ----------------

function openCart() {
    document.getElementById("cartModal").classList.remove("hidden");
    renderCart();
}

function closeCart() {
    document.getElementById("cartModal").classList.add("hidden");
}

function renderCart() {
    const container = document.getElementById("cartItems");
    container.innerHTML = "";

    cart.forEach((item, index) => {
        const color = colors.find(c => c.id === item.color_id);
        if (!color) return;

        container.innerHTML += `
            <div class="cart-item">
                <div>
                    ${color.article} — ${item.weight} кг
                </div>

                <div class="cart-item-controls">
                    <button class="button small"
                        onclick="increaseWeight(${index})">+</button>
                    <button class="button small"
                        onclick="decreaseWeight(${index})">-</button>
                    <button class="button small danger"
                        onclick="removeFromCart(${index})">✕</button>
                </div>
            </div>
        `;
    });
}

// ---------------- CHECKOUT ----------------

function openCheckout() {
    if (cart.length === 0) return;
    document.getElementById("checkoutModal").classList.remove("hidden");
}

function closeCheckout() {
    document.getElementById("checkoutModal").classList.add("hidden");
}

// ---------------- CONFIRM ORDER ----------------

async function confirmOrder() {

    const firstName = document.getElementById("firstName").value.trim();
    const lastName = document.getElementById("lastName").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const address = document.getElementById("address").value.trim();
    const deliveryMethod = document.getElementById("deliveryMethod").value;

    if (!firstName || !phone) {
        alert("Заполните обязательные поля");
        return;
    }

    if (cart.length === 0) {
        alert("Корзина пуста");
        return;
    }

    const payload = {
        user_id: userId,
        items: cart,
        first_name: firstName,
        last_name: lastName,
        phone,
        address,
        delivery_method: deliveryMethod
    };

    try {
        const res = await fetch("/api/confirm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            cart = [];
            saveCart();
            closeCheckout();
            closeCart();
            await loadColors();

            alert("Ваш заказ принят.");

            if (tg) {
                tg.HapticFeedback.notificationOccurred("success");
            }

        } else {
            alert(data.detail || "Ошибка при оформлении");
        }

    } catch {
        alert("Ошибка соединения с сервером");
    }
}

// ---------------- AUTO REFRESH ----------------

setInterval(loadColors, 10000);

// ---------------- INIT ----------------

updateCartBar();
loadColors();