export const API_BASE_URL = 'http://192.168.111.40:5000';

export const API_PATHS = {
    LOGIN: '/api/login',
    IPS: '/api/ips',
    PROCESS: '/api/process',
    WHITELIST_STATUS: '/api/whitelist/status',
    SETTINGS_THRESHOLD: '/api/settings/threshold',
    CHANGE_PASSWORD: '/api/change-password',
    DOWNLOAD: (filename) => `/api/download/${filename}`,
    TASK_STATUS: '/api/task-status'
};

export const API_URLS = {
    ...Object.entries(API_PATHS).reduce((acc, [key, path]) => {
        if (typeof path === 'function') {
            acc[key] = path;
        } else {
            acc[key] = `${API_BASE_URL}${path}`;
        }
        return acc;
    }, {}),
    API_BASE_URL
}; 