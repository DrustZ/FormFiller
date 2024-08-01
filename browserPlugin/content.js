// Utility function to get the visible label text for a form field
function getFieldLabel(element) {
    // Check for a label element associated with the input
    const id = element.id;
    if (id) {
        const label = document.querySelector(`label[for="${id}"]`);
        if (label) {
            return label.textContent.trim();
        }
    }
    
    // Check for a parent label element
    const parentLabel = element.closest('label');
    if (parentLabel) {
        return parentLabel.textContent.trim().replace(element.value, '').trim();
    }
    
    // Check for preceding text node
    const previousSibling = element.previousSibling;
    if (previousSibling && previousSibling.nodeType === Node.TEXT_NODE) {
        return previousSibling.textContent.trim();
    }
    
    // If no label found, return the name attribute or placeholder
    return element.name || element.placeholder || 'Unlabeled Field';
}

// Function to check if an element is visible
function isElementVisible(element) {
    return !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
}

// Function to check if a field is relevant for form filling
function isRelevantFormField(element) {
    const type = element.type.toLowerCase();
    const name = element.name.toLowerCase();
    
    // Exclude hidden, submit, reset, button, and image input types
    if (['hidden', 'submit', 'reset', 'button', 'image'].includes(type)) {
        return false;
    }
    
    // Exclude fields that are likely not meant for user input
    const excludedNames = ['csrf', 'token', '_token', 'captcha'];
    if (excludedNames.some(excluded => name.includes(excluded))) {
        return false;
    }
    
    // Check if the element is visible
    return isElementVisible(element);
}

function setFieldValue(element, value) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    nativeInputValueSetter.call(element, value);

    const ev2 = new Event('input', { bubbles: true});
    element.dispatchEvent(ev2);

    const event = new Event('change', { bubbles: true });
    element.dispatchEvent(event);
}

// Utility functions (getFieldLabel, isElementVisible, isRelevantFormField) remain the same

function getWebsiteOverview() {
    const title = document.title;
    const metaDescription = document.querySelector('meta[name="description"]')?.content || '';
    const h1 = document.querySelector('h1')?.textContent || '';
    // const mainContent = dcument.querySelector('main')?.textContent || document.body.textContent;
    
    return `
    Title: ${title}
    Description: ${metaDescription}
    Main Heading: ${h1}
    `.trim();
}

function getFormFields() {
    const fields = [];
    const forms = document.forms;
    
    for (let form of forms) {
        const formElements = form.elements;
        for (let element of formElements) {
            if (isRelevantFormField(element)) {
                fields.push({
                    id: element.id || element.name,
                    name: getFieldLabel(element),
                    type: element.type.toLowerCase()
                });
            }
        }
    }
    console.log("fields: ", fields);
    return fields;
}

function fillFormFields() {
    const websiteOverview = getWebsiteOverview();
    const formFields = getFormFields();
    
    const dataToSend = {
        websiteOverview: websiteOverview,
        formFields: formFields,
        url: window.location.href
    };
    
    chrome.runtime.sendMessage({ action: 'postData', data: dataToSend }, (response) => {
        if (response.fieldValues) {
            fillFormWithServerData(response.fieldValues);
            chrome.runtime.sendMessage({ action: 'formsFilled', success: true });
        } else {
            chrome.runtime.sendMessage({ action: 'formsFilled', success: false });
        }
    });
    return;
}

function fillFormWithServerData(fieldValues) {
    console.log('Filling form with server data:', fieldValues);
    
    for (let field of fieldValues) {
        const element = document.getElementById(field.id) || document.getElementsByName(field.id)[0];
        if (element) {
            if (element.type === 'checkbox' || element.type === 'radio') {
                element.checked = field.answer === true || field.answer === 'true';
            } else if (element.tagName === 'SELECT') {
                const option = Array.from(element.options).find(opt => opt.value === field.answer || opt.text === field.answer);
                if (option) {
                    option.selected = true;
                }
            } else {
                element.value = field.answer;
            }
            
            // Trigger events to simulate user input
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        // Log for debugging
        console.log(`Filled field: ${field.name} (${field.id}) with value: ${field.answer}`);
    }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "fillForms") {
        fillFormFields();
    }
});