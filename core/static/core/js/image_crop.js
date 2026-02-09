(function () {
    "use strict";

    var CROP_SIZE = 512;
    var modal = null;
    var cropper = null;
    var currentInput = null;
    var currentFileName = null;

    function getModal() {
        if (modal) return modal;
        var div = document.createElement("div");
        div.id = "image-crop-modal";
        div.innerHTML =
            '<div class="image-crop-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;">' +
            '<div class="image-crop-box" style="background:#fff;border-radius:8px;max-width:90vw;max-height:90vh;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,.25);">' +
            '<div class="image-crop-container" style="max-height:70vh;width:400px;height:400px;background:#000;">' +
            '<img id="image-crop-img" src="" alt="" style="max-width:100%;max-height:100%;display:block;">' +
            "</div>" +
            '<div class="image-crop-actions" style="padding:16px;display:flex;gap:12px;justify-content:flex-end;border-top:1px solid #e5e7eb;">' +
            '<button type="button" class="image-crop-cancel" style="padding:8px 16px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;">İptal</button>' +
            '<button type="button" class="image-crop-apply" style="padding:8px 16px;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer;">Kırp ve yükle</button>' +
            "</div>" +
            "</div>" +
            "</div>";
        div.style.display = "none";
        document.body.appendChild(div);
        modal = div;

        div.querySelector(".image-crop-cancel").addEventListener("click", closeModal);
        div.querySelector(".image-crop-apply").addEventListener("click", applyCrop);
        return div;
    }

    function closeModal() {
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
        currentInput = null;
        currentFileName = null;
        if (modal) {
            modal.style.display = "none";
        }
    }

    function applyCrop() {
        if (!cropper || !currentInput) {
            closeModal();
            return;
        }
        var canvas = cropper.getCroppedCanvas({ width: CROP_SIZE, height: CROP_SIZE });
        if (!canvas) {
            closeModal();
            return;
        }
        canvas.toBlob(
            function (blob) {
                if (!blob || !currentInput) {
                    closeModal();
                    return;
                }
                var name = currentFileName || "image.png";
                if (!/\.(jpe?g|png|gif|webp)$/i.test(name)) name = name.replace(/\.[^.]+$/, "") + ".png";
                var file = new File([blob], name, { type: blob.type });
                var dt = new DataTransfer();
                dt.items.add(file);
                currentInput.files = dt.files;
                if (currentInput.dispatchEvent) {
                    currentInput.dispatchEvent(new Event("change", { bubbles: true }));
                }
                closeModal();
            },
            "image/png",
            0.95
        );
    }

    function openCropModal(input, file) {
        if (!file || !file.type.match(/^image\//)) return;
        currentInput = input;
        currentFileName = file.name;
        var reader = new FileReader();
        reader.onload = function (e) {
            var m = getModal();
            var img = m.querySelector("#image-crop-img");
            img.src = e.target.result;
            m.style.display = "block";
            if (cropper) cropper.destroy();
            cropper = new Cropper(img, {
                aspectRatio: 1,
                viewMode: 1,
                dragMode: "move",
                autoCropArea: 0.8,
                restore: false,
            });
        };
        reader.readAsDataURL(file);
    }

    function init() {
        if (typeof Cropper === "undefined") return;
        document.querySelectorAll(".image-crop-input").forEach(function (input) {
            if (input.dataset.cropInit) return;
            input.dataset.cropInit = "1";
            input.addEventListener("change", function () {
                var file = input.files && input.files[0];
                if (file) {
                    openCropModal(input, file);
                }
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
    if (typeof django !== "undefined" && django.jQuery) {
        django.jQuery(document).on("formset:added", init);
    }
})();
