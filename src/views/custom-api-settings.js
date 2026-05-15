import { xf } from '../functions.js';

class CustomApiSettings extends HTMLElement {
    connectedCallback() {
        this.urlInput = this.querySelector('#custom-api--url--input');
        this.keyInput = this.querySelector('#custom-api--key--input');
        this.saveBtn  = this.querySelector('#custom-api--save');

        this.urlInput.value = localStorage.getItem('customApiUrl') ?? '';
        this.keyInput.value = localStorage.getItem('customApiKey') ?? '';

        this.saveBtn.addEventListener('click', () => {
            xf.dispatch('ui:custom-api:url-set', this.urlInput.value.trim());
            xf.dispatch('ui:custom-api:key-set', this.keyInput.value.trim());
        });
    }
}

customElements.define('custom-api-settings', CustomApiSettings);
