document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    loadAllSections();

    function loadAllSections() {
        fetch('/get_all_sections')
            .then(response => response.json())
            .then(sections => {
                // Clear existing sections
                const container = document.querySelector('.container');
                // Keep the "Add new list" button
                const addButton = document.getElementById('add-section-btn');
                container.innerHTML = '';
                container.appendChild(addButton);
                
                // Create UI for each section
                sections.forEach(section => {
                    createSectionUI(section);
                    
                    // Populate the shopping and saved items
                    section.shopping_items.forEach(item => {
                        addItemToShoppingList(item, section.id);
                    });
                    section.saved_items.forEach(item => {
                        addItemToSavedList(item, section.id);
                    });
                });
            })
            .catch(error => {
                console.error('Error loading sections:', error);
            });
    }

    function createSectionUI(section) {
        const container = document.querySelector('.container');
        
        const newSection = document.createElement('div');
        newSection.classList.add('section');
        newSection.dataset.sectionId = section.id;
    
        newSection.innerHTML = `
            <div class="list saved-groceries">
                <h2>${section.name} שמור</h2>
                <form class="grocery-form" onsubmit="event.preventDefault(); addSavedItem(${section.id});">
                    <input type="text" name="grocery_name" placeholder="מוצר חדש" style="width: 50%; display: inline-block; margin-bottom: 10px;">
                    <input type="submit" value="הוסף" style="margin-bottom: 10px;">
                </form>
                <ul class="saved-list" data-section-id="${section.id}">
                </ul>
                <button onclick="addAllSavedItems(${section.id})">הוסף את כל המוצרים</button>
            </div>
    
            <div class="list shopping-list">
                <div class="section-header">
                    <h2>${section.name}</h2>
                    <button class="delete-section-btn">×</button>
                </div>
                <ul class="current-list" data-section-id="${section.id}">
                </ul>
            </div>

        `;

        const deleteBtn = newSection.querySelector('.delete-section-btn');
        deleteBtn.addEventListener('click', () => {
            if (confirm(`האם אתה בטוח שברצונך למחוק את הרשימה "${section.name}"?`)) {
                socket.emit('delete_section', { section_id: section.id });
            }
        });

        container.appendChild(newSection);
    }

    function addItemToShoppingList(item, sectionId) {
        const shoppingList = document.querySelector(`.current-list[data-section-id="${sectionId}"]`);
        const listItem = document.createElement('li');
        listItem.textContent = item;
        listItem.addEventListener('click', () => {
            socket.emit('remove_item', { item, section_id: sectionId });
        });
        shoppingList.appendChild(listItem);
    }

    function addItemToSavedList(item, sectionId) {
        const savedList = document.querySelector(`.saved-list[data-section-id="${sectionId}"]`);
        const listItem = document.createElement('li');
        listItem.textContent = item;
        listItem.classList.add('clickable');

        listItem.addEventListener('click', () => {
            socket.emit('add_item', { item, section_id: sectionId });
        });

        const removeBtn = document.createElement('button');
        removeBtn.classList.add('remove-btn');
        removeBtn.textContent = 'X';
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            socket.emit('remove_saved_item', { item, section_id: sectionId });
        });

        listItem.appendChild(removeBtn);
        savedList.appendChild(listItem);
    }

    // Handle section creation
    window.addSection = function() {
        const sectionName = prompt("שם הרשימה שברצונך להוסיף:");
        if (!sectionName) {
            alert("הרשימה צריכה שם!");
            return;
        }
        socket.emit('create_section', { name: sectionName });
    };

    // Handle adding saved items
    window.addSavedItem = function(sectionId) {
        const section = document.querySelector(`.section[data-section-id="${sectionId}"]`);
        const input = section.querySelector('input[name="grocery_name"]');
        const itemName = input.value.trim();
        
        if (itemName) {
            socket.emit('add_saved_item', { item: itemName, section_id: sectionId });
            input.value = '';
        }
    };

    // Handle adding all saved items to shopping list
    window.addAllSavedItems = function(sectionId) {
        const savedItems = document.querySelector(`.saved-list[data-section-id="${sectionId}"]`).getElementsByTagName('li');
        Array.from(savedItems).forEach(item => {
            const itemName = item.textContent.slice(0, -1).trim();
            socket.emit('add_item', { item: itemName, section_id: sectionId });
        });
    };

    // Socket event listeners
    socket.on('section_created', (section) => {
        createSectionUI(section);
    });

    socket.on('section_deleted', (data) => {
        const sectionToRemove = document.querySelector(`.section[data-section-id="${data.section_id}"]`);
        if (sectionToRemove) {
            sectionToRemove.remove();
        }
    });

    socket.on('update_list', (data) => {
        const shoppingList = document.querySelector(`.current-list[data-section-id="${data.section_id}"]`);
        shoppingList.innerHTML = '';
        data.items.forEach(item => addItemToShoppingList(item, data.section_id));
    });

    socket.on('update_saved_list', (data) => {
        const savedList = document.querySelector(`.saved-list[data-section-id="${data.section_id}"]`);
        savedList.innerHTML = '';
        data.items.forEach(item => addItemToSavedList(item, data.section_id));
    });

    socket.on('connect', () => {
        // Reload all sections when reconnecting
        loadAllSections();
    });

    // Add reconnection handling
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });

    socket.on('reconnect', () => {
        console.log('Reconnected to server');
        loadAllSections();
    });

    // Add click handler for the add section button
    document.getElementById('add-section-btn').addEventListener('click', addSection);
});