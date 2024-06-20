document.addEventListener('DOMContentLoaded', function () {
    var cab = document.getElementById('cab');
    if (cab) {
      cab.addEventListener('click', function (e) {
        // Предотвращение действия по умолчанию (например, переход по ссылке)
        e.preventDefault();
        // Перенаправление на окно регистрации
        redirectToRegistration();
        // Скрытие контекстного меню (если это необходимо)
        hideContextMenu();
      });
    }
  });
  
  // Определение функции для перенаправления на окно регистрации
  function redirectToRegistration() {
    // Используй window.location.href для перенаправления на другую страницу
    window.location.href = "/login";
  }