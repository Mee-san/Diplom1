document.addEventListener("DOMContentLoaded", function() {
    const toggleBtn = document.querySelector(".toggle-btn");
    const sidebar = document.querySelector(".sidebar");

    // Обработчик для кнопки открытия/закрытия панели
    toggleBtn.addEventListener("click", function() {
        sidebar.classList.toggle("visible");
    });

    // Обработчик для кнопки "На главную"
    const returnBtn = document.querySelector(".return-to-main-button");
    returnBtn.addEventListener("click", function() {
        window.location.href = "/";
    });

    // Обработчик для кнопки "Вернуться на dashboard"
    const returnToDashboardBtn = document.querySelector(".return-to-dashboard-button");
    returnToDashboardBtn.addEventListener("click", function() {
        window.location.href = "/dashboard"; // Поменяйте "/dashboard" на соответствующий путь к вашей странице dashboard
    });

    // Обновление позиции панели и кнопки при прокрутке
    function updatePosition() {
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        const offset = 10; // отступ сверху в пикселях

        sidebar.style.top = `${offset + scrollTop}px`;
        toggleBtn.style.top = `${scrollTop + 10}px`;
    }

    // Событие прокрутки
    window.addEventListener('scroll', updatePosition);

    // Вызываем функцию при загрузке страницы для установки начального положения
    updatePosition();
    
    // Обработчик для кнопки "Genres"
    const returnToGenresBtn = document.querySelector(".return-to-genres-button");
    returnToGenresBtn.addEventListener("click", function() {
        window.location.href = "/genres";
    });

    // Обработчик для кнопки "News"
    const returnToNewsBtn = document.querySelector(".return-to-news-button");
    returnToNewsBtn.addEventListener("click", function() {
        window.location.href = "/news";
    });

    // Обработчик для кнопки "Shop"
    const returnToShopBtn = document.querySelector(".return-to-shop-button");
    returnToShopBtn.addEventListener("click", function() {
        window.location.href = "/Shop";
    });
    
    // Обработчик для кнопки "Корзина"
    const returnToCartBtn = document.querySelector(".return-to-cart-button");
    returnToCartBtn.addEventListener("click", function() {
        window.location.href = "/cart";
    });

    // Обработчик для кнопки "Обратная связь"
    const returnToFeedbackBtn = document.querySelector(".return-to-feedback-button");
    returnToFeedbackBtn.addEventListener("click", function() {
        // Здесь можете добавить логику для открытия формы обратной связи или перехода по ссылке
        window.location.href = "/feedback";
    });
    
});
