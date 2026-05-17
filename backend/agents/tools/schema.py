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
    }
]
