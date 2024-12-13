// Card CRUD Operations
function editCard(cardId) {
    const titleElement = document.getElementById(`card-title-${cardId}`);
    const contentElement = document.getElementById(`card-content-${cardId}`);
    
    // Populate modal with current content
    document.getElementById('editCardTitle').value = titleElement.textContent;
    document.getElementById('editCardContent').value = contentElement.textContent.trim();
    document.getElementById('editCardId').value = cardId;
    
    // Show modal
    const editModal = new bootstrap.Modal(document.getElementById('editCardModal'));
    editModal.show();
}

function deleteCard(cardId) {
    if (confirm('Are you sure you want to delete this card?')) {
        fetch(`/api/cards/${cardId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const cardElement = document.getElementById(`card-${cardId}`);
                cardElement.remove();
            } else {
                alert('Failed to delete card');
            }
        });
    }
}

// Save card changes
function saveCardChanges() {
    const cardId = document.getElementById('editCardId').value;
    const title = document.getElementById('editCardTitle').value;
    const content = document.getElementById('editCardContent').value;
    
    fetch(`/api/cards/${cardId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: title,
            content: content
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update card content
            document.getElementById(`card-title-${cardId}`).textContent = title;
            document.getElementById(`card-content-${cardId}`).textContent = content;
            
            // Close modal
            const editModal = bootstrap.Modal.getInstance(document.getElementById('editCardModal'));
            editModal.hide();
        } else {
            alert('Failed to update card');
        }
    });
}
