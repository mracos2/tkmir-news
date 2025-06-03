fetch('/api/feedbacks') // Укажите путь к вашему API-скрипту
    .then(response => response.json())
    .then(data => {
        const tableBody = document.getElementById('feedbacksTable').getElementsByTagName('tbody')[0];
        if (data && !data.error) {
            data.forEach(feedback => {
                let row = tableBody.insertRow();
                let idCell = row.insertCell();
                let createdAtCell = row.insertCell();
                let nameCell = row.insertCell();
                let emailCell = row.insertCell();
                let phoneCell = row.insertCell();
                let messageCell = row.insertCell();

                idCell.textContent = feedback.id;
                createdAtCell.textContent = feedback.created_at;
                nameCell.textContent = feedback.name;
                emailCell.textContent = feedback.email;
                phoneCell.textContent = feedback.phone;
                messageCell.textContent = feedback.message;
            });
        } else {
            // Обработка ошибок, например, вывод сообщения об ошибке
            let row = tableBody.insertRow();
            let cell = row.insertCell();
            cell.colSpan = 6;  // Занимает всю ширину таблицы
            cell.textContent = data.error || "Failed to load feedbacks.";
        }
    })
    .catch(error => {
        console.error('Error fetching feedbacks:', error);
        const tableBody = document.getElementById('feedbacksTable').getElementsByTagName('tbody')[0];
        let row = tableBody.insertRow();
        let cell = row.insertCell();
        cell.colSpan = 6;  // Занимает всю ширину таблицы
        cell.textContent = "Failed to load feedbacks.";  // Отображаем сообщение об ошибке
    });