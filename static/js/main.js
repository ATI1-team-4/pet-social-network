/**
 * Funciones globales para control de modales en Petly.
 */
if (!window.openModal) {
    window.openModal = function(modalId, onConfirm) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.onConfirmCallback = onConfirm;
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.body.classList.add('overflow-hidden');
    };

    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.add('hidden');
        modal.classList.remove('flex');
        document.body.classList.remove('overflow-hidden');
        modal.onConfirmCallback = null;
    };

    window.confirmModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        if (typeof modal.onConfirmCallback === 'function') {
            modal.onConfirmCallback();
        }

        const codigo = modal.getAttribute('data-onconfirm');
        if (codigo) {
            try {
                window.eval(codigo);
            } catch (error) {
                console.error('Error al ejecutar onconfirm:', error);
            }
        }

        window.closeModal(modalId);
    };

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const modalActivo = document.querySelector('[data-petly-modal]:not(.hidden)');
            if (modalActivo) {
                window.closeModal(modalActivo.id);
            }
        }
    });
}
