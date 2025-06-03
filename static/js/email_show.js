fetch('/api/emails')  // Укажите путь к вашему API-скрипту
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('emailsTable').getElementsByTagName('tbody')[0];
        if (data && !data.error) {
            data.forEach(email => {
                let row = tableBody.insertRow();
                let idCell = row.insertCell();
                let emailCell = row.insertCell();
                let createdAtCell = row.insertCell();

                idCell.textContent = email.id;
                emailCell.textContent = email.email;
                createdAtCell.textContent = email.created_at;
            });
        } else {
            // Обработка ошибок, например, вывод сообщения об ошибке
            let row = tableBody.insertRow();
            let cell = row.insertCell();
            cell.colSpan = 3;  // Занимает всю ширину таблицы
            cell.textContent = data.error || "Failed to load emails.";
        }
    })
    .catch(error => {
        console.error('Error fetching emails:', error);
        const tableBody = document.getElementById('emailsTable').getElementsByTagName('tbody')[0];
        let row = tableBody.insertRow();
        let cell = row.insertCell();
        cell.colSpan = 3;  // Занимает всю ширину таблицы
        cell.textContent = "Failed to load emails.";  // Отображаем сообщение об ошибке
    });