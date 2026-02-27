let adminToken = localStorage.getItem("admin_token") || null;

function showAdminPanel() {
    document.getElementById("loginSection").classList.add("hidden");
    document.getElementById("adminPanel").classList.remove("hidden");
    loadAdminColors();
}

function adminLogin() {

    const username = document.getElementById("adminUser").value;
    const password = document.getElementById("adminPass").value;

    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    fetch("/admin/login", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        if (data.token) {
            adminToken = data.token;
            localStorage.setItem("admin_token", adminToken);
            showAdminPanel();
        } else {
            alert("Ошибка входа");
        }

    });
}

function loadAdminColors() {

    fetch("/admin/colors", {
        headers: {
            "Authorization": "Bearer " + adminToken
        }
    })
    .then(res => res.json())
    .then(colors => {

        const container = document.getElementById("adminColors");
        container.innerHTML = "";

        colors.forEach(color => {

            container.innerHTML += `
                <div class="card">
                    <div><strong>${color.article}</strong> — ${color.name}</div>
                    <div>Собрано: ${color.total_weight} кг</div>
                    <div>Статус: ${color.status}</div>
                    <button onclick="closeParty(${color.id})">
                        Закрыть вручную
                    </button>
                </div>
            `;
        });

    });
}

function addColor() {

    const article = document.getElementById("article").value;
    const name = document.getElementById("name").value;
    const format = document.getElementById("format").value;
    const imageUrl = document.getElementById("imageUrl").value;

    const formData = new FormData();
    formData.append("article", article);
    formData.append("name", name);
    formData.append("format", format);
    formData.append("image_url", imageUrl);

    fetch("/admin/add", {
        method: "POST",
        headers: {
            "Authorization": "Bearer " + adminToken
        },
        body: formData
    })
    .then(res => res.json())
    .then(() => {
        loadAdminColors();
    });
}

function closeParty(id) {

    fetch(`/admin/close/${id}`, {
        method: "POST",
        headers: {
            "Authorization": "Bearer " + adminToken
        }
    })
    .then(() => {
        loadAdminColors();
    });
}

if (adminToken) {
    showAdminPanel();
}