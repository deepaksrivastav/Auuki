import { LocalStorageItem } from '../storage/local-storage.js';

const urlStorage = LocalStorageItem({ key: 'customApiUrl', fallback: '', parse: String, encode: String });
const keyStorage = LocalStorageItem({ key: 'customApiKey', fallback: '', parse: String, encode: String });

function isConfigured() {
    const url = urlStorage.restore();
    const key = keyStorage.restore();
    return url !== '' && key !== '';
}

async function uploadWorkout(record) {
    const url = urlStorage.restore();
    const key = keyStorage.restore();

    const formData = new FormData();
    formData.append('file', record.blob, 'activity.fit');
    formData.append('name', record.summary?.name ?? 'Powered by Auuki workout');

    try {
        const response = await fetch(`${url}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${key}` },
            body: formData,
        });
        if(response.ok) {
            console.log(':custom-api :upload :success');
            return ':success';
        }
        console.log(':custom-api :upload :fail', response.status);
        return ':fail';
    } catch(error) {
        console.log(':custom-api :upload :error', error);
        return ':fail';
    }
}

export default { isConfigured, uploadWorkout };
