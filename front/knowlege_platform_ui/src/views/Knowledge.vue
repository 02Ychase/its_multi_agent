<template>
  <div class="knowledge-container">
    <div class="page-header">
      <h2>知识库管理</h2>
      <p class="subtitle">上传和管理知识库文档，支持 .md、.txt、.docx、.pdf 格式</p>
    </div>

    <el-card class="upload-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><UploadFilled /></el-icon>
          <span>文件上传</span>
        </div>
      </template>
      <el-upload
        class="upload-area"
        drag
        action=""
        :http-request="handleUpload"
        multiple
        :show-file-list="false"
      >
        <div class="upload-content">
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">拖拽文件到此处，或 <em>点击上传</em></div>
          <div class="upload-tip">支持 .md、.txt、.docx、.pdf 格式文件</div>
        </div>
      </el-upload>
    </el-card>

    <div v-if="uploadHistory.length > 0" class="history-section">
      <h3>上传记录</h3>
      <el-card shadow="never" class="history-card">
        <el-table :data="uploadHistory" style="width: 100%" :row-class-name="tableRowClassName">
          <el-table-column prop="fileName" label="文件名" min-width="200" />
          <el-table-column prop="chunks" label="切片数" width="100" align="center" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'" size="small" effect="light">
                {{ scope.row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="信息" min-width="200" />
          <el-table-column prop="time" label="时间" width="180" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadFile } from '@/api/knowledge'
import { ElMessage } from 'element-plus'

const uploadHistory = ref([])

const handleUpload = async (options) => {
  const { file } = options
  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await uploadFile(formData)
    uploadHistory.value.unshift({
      fileName: res.file_name,
      chunks: res.chunks_added,
      status: res.status,
      message: res.message,
      time: new Date().toLocaleString()
    })
    ElMessage.success(`${file.name} 上传成功`)
  } catch (error) {
    uploadHistory.value.unshift({
      fileName: file.name,
      chunks: 0,
      status: 'error',
      message: error.message || '上传失败',
      time: new Date().toLocaleString()
    })
    ElMessage.error(`${file.name} 上传失败`)
  }
}

const tableRowClassName = ({ rowIndex }) => {
  if (rowIndex === 0) return 'success-row'
  return ''
}
</script>

<style lang="scss" scoped>
.knowledge-container {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

  h2 {
    color: var(--text-primary);
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 6px;
  }

  .subtitle {
    color: var(--text-muted);
    font-size: 14px;
  }
}

.upload-card {
  margin-bottom: 32px;
  border: 1px solid var(--color-border);
  border-radius: 12px;

  :deep(.el-card__header) {
    border-bottom: 1px solid var(--color-border);
    padding: 16px 20px;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 15px;
    color: var(--text-primary);
  }
}

.upload-area {
  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
    background-color: var(--color-surface-raised);
    border: 2px dashed var(--color-border);
    border-radius: 10px;
    padding: 40px 20px;
    transition: all 0.2s ease;

    &:hover {
      border-color: var(--color-accent);
      background-color: var(--color-accent-light);
    }
  }

  .upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .upload-icon {
    font-size: 40px;
    color: var(--color-accent);
    margin-bottom: 4px;
  }

  .upload-text {
    font-size: 15px;
    color: var(--text-secondary);

    em {
      color: var(--color-accent);
      font-style: normal;
      font-weight: 600;
    }
  }

  .upload-tip {
    font-size: 13px;
    color: var(--text-muted);
  }
}

.history-section {
  h3 {
    color: var(--text-primary);
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 16px;
  }

  .history-card {
    border: 1px solid var(--color-border);
    border-radius: 12px;
    overflow: hidden;

    :deep(.el-table) {
      --el-table-border-color: var(--color-border);
      --el-table-header-bg-color: var(--color-surface-raised);
      --el-table-row-hover-bg-color: var(--color-accent-light);
    }

    :deep(.el-table th) {
      font-weight: 600;
      color: var(--text-primary);
    }

    :deep(.el-table td) {
      color: var(--text-secondary);
    }
  }
}
</style>
