document.addEventListener('DOMContentLoaded', function() {
    // Находит все видимые кнопки submit
    document.querySelectorAll('form button[type="submit"], form input[type="submit"]').forEach(function(btn) {
        // Пропускаем, если уже стилизована
        if (!btn.classList.contains('vetmis-med-btn')) {
            btn.classList.add('vetmis-med-btn');

            // Добавляет медицинскую иконку, если нет
            if (btn.tagName.toLowerCase() === 'button' && !btn.querySelector('.bi')) {
                let span = document.createElement('span');
                span.className = 'bi bi-activity me-2';
                btn.prepend(span);
            }
            if (btn.tagName.toLowerCase() === 'input' && btn.value) {
                btn.value = '⛑ ' + btn.value;
            }
        }
    });
});