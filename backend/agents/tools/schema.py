NATIVE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Jalankan bash command di terminal. Gunakan untuk install dependencies, start server, atau command line utility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Bash command yang akan dieksekusi."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Baca isi dari sebuah file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path absolute atau relative file yang akan dibaca."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Tulis atau timpa isi sebuah file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path tempat file akan ditulis."},
                    "content": {"type": "string", "description": "Isi lengkap dari file yang akan ditulis."},
                    "confirm": {"type": "boolean", "description": "Konfirmasi jika menimpa file penting."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_model",
            "description": "Tanya model AI lain untuk tugas spesifik atau meminta pendapat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "ID model yang akan ditanya (misal: 'gpt-4o')."},
                    "prompt": {"type": "string", "description": "Pertanyaan atau tugas untuk model tersebut."}
                },
                "required": ["model_id", "prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Cari informasi di internet via DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Kata kunci pencarian."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_safe_port",
            "description": "Cari port yang kosong dan aman digunakan untuk menjalankan server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preferred": {"type": "integer", "description": "Port yang diinginkan (opsional)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Tampilkan isi folder dengan metadata (seperti ls -la).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path direktori yang akan dilist."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_tree",
            "description": "Tampilkan struktur folder secara visual (seperti command tree).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path direktori root."},
                    "max_depth": {"type": "integer", "description": "Maksimal kedalaman tree (default: 4)."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Cari file berdasarkan nama, pattern (wildcard), atau ekstensi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Pattern pencarian (misal: '*.py')."},
                    "search_path": {"type": "string", "description": "Direktori tempat mencari."},
                    "file_type": {"type": "string", "description": "Tipe file ('file', 'dir', 'any')."}
                },
                "required": ["pattern", "search_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_files",
            "description": "Cari teks atau keyword di dalam konten file (seperti grep -r).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Teks yang dicari."},
                    "search_path": {"type": "string", "description": "Direktori tempat pencarian."},
                    "extensions": {"type": "string", "description": "Filter ekstensi file (misal: '.py,.js')."}
                },
                "required": ["keyword", "search_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "make_directory",
            "description": "Buat direktori baru beserta direktori parent-nya jika belum ada (mkdir -p).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path direktori yang akan dibuat."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Pindahkan atau rename file/folder (mv).",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Path sumber."},
                    "destination": {"type": "string", "description": "Path tujuan."}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Salin file atau folder (cp -r).",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Path sumber yang akan disalin."},
                    "destination": {"type": "string", "description": "Path tujuan salinan."}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Hapus file atau folder secara permanen (rm -rf).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path file/folder yang akan dihapus."},
                    "confirm": {"type": "boolean", "description": "Set true untuk folder besar/file penting."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_path",
            "description": "Ambil path absolute dari project yang sedang aktif di session ini.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_project_path",
            "description": "Simpan path project aktif untuk digunakan di pemanggilan tool selanjutnya.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path absolute ke folder project."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_projects",
            "description": "Lihat semua history project yang pernah dibuat.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Ambil metadata detail sebuah file atau direktori (size, mod time, permissions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path file/direktori."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Baca konten dari dokumen Office atau PDF (mendukung .pdf, .docx, .xlsx, .pptx, .csv, .txt).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path file dokumen yang akan dibaca."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Lakukan pengeditan surgikal/sebagian pada file dengan mencari teks lama dan menggantinya dengan teks baru.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path file yang akan diedit."},
                    "old_string": {"type": "string", "description": "Teks persis (literal) yang akan diganti."},
                    "new_string": {"type": "string", "description": "Teks baru sebagai penggantinya."}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Buka dan navigasi ke sebuah URL menggunakan browser headless. Gunakan untuk mengakses website, scraping, atau otomasi web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL yang akan dibuka (contoh: https://example.com)."},
                    "session_id": {"type": "string", "description": "ID sesi browser (opsional, untuk mempertahankan session)."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Klik elemen di halaman browser menggunakan CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector elemen yang akan diklik (contoh: '#submit-btn', '.btn-primary')."},
                    "session_id": {"type": "string", "description": "ID sesi browser (opsional)."}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Isi teks ke dalam field input di browser (seperti form input, search box, dll).",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector field input."},
                    "text": {"type": "string", "description": "Teks yang akan diisi."},
                    "session_id": {"type": "string", "description": "ID sesi browser (opsional)."}
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_extract_text",
            "description": "Ambil seluruh teks yang terlihat dari halaman web saat ini di browser. Gunakan setelah browser_navigate untuk membaca konten halaman.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "ID sesi browser (opsional)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Ambil screenshot halaman browser saat ini dan simpan sebagai file PNG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nama file screenshot yang akan disimpan (tanpa ekstensi, contoh: 'hasil_scraping')."},
                    "session_id": {"type": "string", "description": "ID sesi browser (opsional)."}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate gambar dari deskripsi teks menggunakan AI image generation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Deskripsi gambar yang ingin dibuat (dalam bahasa Inggris untuk hasil terbaik)."},
                    "size": {"type": "string", "description": "Ukuran gambar: '1024x1024' (default), '1792x1024' (landscape), '1024x1792' (portrait)."},
                    "quality": {"type": "string", "description": "Kualitas: 'standard' (default) atau 'hd'."}
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "Jadwalkan tugas atau pengingat proaktif yang akan dieksekusi secara otomatis di masa depan. Gunakan saat user meminta diingatkan, penjadwalan otomatis, atau eksekusi berulang.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Judul singkat tugas terjadwal (maks 100 karakter)."},
                    "description": {"type": "string", "description": "Instruksi lengkap yang akan dijalankan saat waktu tiba."},
                    "due_in_minutes": {"type": "integer", "description": "Berapa menit dari sekarang task akan dieksekusi (default: 60). Contoh: 1440 = 24 jam."},
                    "recurrence": {"type": "string", "description": "Pola perulangan: null (sekali), 'daily' (harian), 'weekly' (mingguan), atau cron expression."}
                },
                "required": ["title", "description"]
            }
        }
    }
]

