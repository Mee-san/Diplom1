function uploadAvatar() {
    // Получаем файл из элемента input
    var avatarInput = document.getElementById('avatar');
    var file = avatarInput.files[0];
    
    // Создаем объект FormData и добавляем в него файл
    var formData = new FormData();
    formData.append('avatar', file);
    
    // Отправляем данные на сервер с помощью fetch
    fetch('/update_avatar', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Ошибка при загрузке файла');
        }
        // Обработка успешного ответа сервера
        console.log('Файл успешно загружен');
        // Можно добавить код для обновления страницы или отображения сообщения об успешной загрузке
    })
    .catch(error => {
        // Обработка ошибок при загрузке файла
        console.error('Ошибка при загрузке файла:', error);
        // Можно добавить код для отображения сообщения об ошибке
    });
}
