<template>
  <div class="uploader-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Upload /></el-icon>
          <span>上传.tif图</span>
          <el-button
            link
            class="tips-button"
            @click="showTips"
          >
            使用说明
          </el-button>
        </div>
      </template>
      
      <div class="upload-content">
        <el-upload
          action=""
          :http-request="uploadFiles"
          multiple
          :show-file-list="false"
          :on-change="onFileChange"
          list-type="text"
          accept=".tif"
          class="upload-section"
          drag
        >
          <el-icon class="upload-icon"><Upload /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">支持多个.tif文件上传</div>
          </template>
        </el-upload>

        <div class="threshold-settings">
          <div class="settings-header">
            <el-icon><Setting /></el-icon>
            <span>孤立点设置</span>
            <el-button 
              link
              class="reset-button"
              @click="resetToDefault"
            >
              重置为默认值
            </el-button>
          </div>
          <div class="form-group">
            <label>白色孤立点大小 (像素):</label>
            <el-input-number 
              v-model="whiteAreaThreshold" 
              :min="0" 
              controls-position="right"
              size="large"
            />
          </div>
          <div class="form-group">
            <label>黑色孤立点大小 (像素):</label>
            <el-input-number 
              v-model="blackAreaThreshold" 
              :min="0" 
              controls-position="right"
              size="large"
            />
          </div>
        </div>
      </div>

      <!-- 处理状态显示 -->
      <div v-if="uploading || loading" class="status-container">
        <div v-if="uploading && !loading" class="upload-status">
          <el-progress
            :percentage="uploadProgress"
            status="active"
            :stroke-width="20"
          />
        </div>

        <div v-if="loading" class="processing-status">
          <div class="processing-content">
            <template v-if="loading && queuePosition > 0">
              <el-icon class="queue-icon" :size="48"><Timer /></el-icon>
              <div class="queue-text">排队等待中...</div>
              <div class="queue-position">前方还有 {{ queuePosition }} 个任务</div>
            </template>
            <template v-else-if="loading && queuePosition === 0">
              <el-icon class="processing-icon" :size="48"><Loading /></el-icon>
              <div class="processing-text">服务器处理中...</div>
              <div class="processing-subtext">请耐心等待，处理完成后会自动显示结果</div>
            </template>
          </div>
        </div>
      </div>
      
      <!-- 处理结果显示 -->
      <el-card v-if="message" class="result-card">
        <template #header>
          <div class="card-header">
            <el-icon :class="alertType === 'success' ? 'success-icon' : 'error-icon'">
              <CircleCheckFilled v-if="alertType === 'success'" />
              <CircleCloseFilled v-if="alertType === 'error'" />
            </el-icon>
            <span>处理结果</span>
          </div>
        </template>
        
        <div class="result-content">
          <el-alert
            :title="message"
            :type="alertType"
            show-icon
            :closable="false"
            class="result-message"
          />
          
          <div v-if="totalFiles !== null && processedFilesCount !== null" class="file-stats">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="上传文件总数">
                {{ totalFiles }}
              </el-descriptions-item>
              <el-descriptions-item label="处理文件数量">
                {{ processedFilesCount }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-card>

      <!-- 下载卡片 -->
      <el-card v-if="zipFile" class="download-card">
        <template #header>
          <div class="card-header">
            <el-icon class="header-icon"><Download /></el-icon>
            <span>下载文件</span>
          </div>
        </template>
        <div class="download-link">
          <el-button 
            type="primary" 
            :icon="Download"
            @click="downloadFile"
            size="large"
          >
            下载处理后的文件
          </el-button>
          <span class="download-tip">点击按钮开始下载</span>
        </div>
      </el-card>
    </el-card>
  </div>
</template>

<script>
import { Upload, Download, Setting, Loading, CircleCheckFilled, CircleCloseFilled, Timer } from '@element-plus/icons-vue'
import { ElNotification } from 'element-plus'
import { h } from 'vue'
import JSZip from 'jszip'
import axios from 'axios'
import { API_URLS } from '@/config/api'

const TaskStatus = {
  QUEUED: 'queued',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
}

const LOCAL_STORAGE_KEY = 'threshold-settings'
let currentNotification = null

export default {
  name: 'FileUploader',
  components: {
    Upload,
    Download,
    Setting,
    Loading,
    CircleCheckFilled,
    CircleCloseFilled,
    Timer
  },
  data() {
    return {
      selectedFiles: [],
      message: '',
      zipFile: null,
      uploading: false,
      uploadProgress: 0,
      loading: false,
      totalFiles: null,
      processedFilesCount: null,
      whiteAreaThreshold: 0,
      blackAreaThreshold: 0,
      alertType: 'info',
      taskId: null,
      queuePosition: 0,
      statusCheckInterval: null
    }
  },
  watch: {
    whiteAreaThreshold() {
      this.saveThresholdSettings()
    },
    blackAreaThreshold() {
      this.saveThresholdSettings()
    }
  },
  mounted() {
    this.loadSettings()
    this.showTips()
    this.initCustomAnimation()
  },
  methods: {
    saveThresholdSettings() {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify({
        whiteAreaThreshold: this.whiteAreaThreshold,
        blackAreaThreshold: this.blackAreaThreshold,
        timestamp: Date.now()
      }))
    },
    async loadSettings() {
      try {
        const localSettings = localStorage.getItem(LOCAL_STORAGE_KEY)
        if (localSettings) {
          const settings = JSON.parse(localSettings)
          this.whiteAreaThreshold = settings.whiteAreaThreshold
          this.blackAreaThreshold = settings.blackAreaThreshold
          return
        }

        const { data } = await axios.get(API_URLS.SETTINGS_THRESHOLD)
        if (data.status === 'success') {
          this.whiteAreaThreshold = data.white_threshold
          this.blackAreaThreshold = data.black_threshold
          this.saveThresholdSettings()
        }
      } catch (error) {
        console.error('加载设置失败:', error)
      }
    },
    async resetToDefault() {
      try {
        const { data } = await axios.get(API_URLS.SETTINGS_THRESHOLD)
        if (data.status === 'success') {
          this.whiteAreaThreshold = data.white_threshold
          this.blackAreaThreshold = data.black_threshold
          this.saveThresholdSettings()
          this.$message.success('已重置为默认值')
        }
      } catch (error) {
        console.error('重置设置失败:', error)
        this.$message.error('重置失败')
      }
    },
    showTips() {
      if (currentNotification) {
        currentNotification.close()
      }
      
      currentNotification = ElNotification({
        title: '使用提示',
        message: h('div', { style: 'margin: 10px 0' }, [
          h('p', { style: 'margin: 5px 0; display: flex; align-items: center;' }, [
            h('i', { class: 'el-icon-warning', style: 'color: var(--el-color-warning); margin-right: 8px' }),
            '1.服务器会自动筛选需要生成的.tif,不需要手动筛选'
          ]),
          h('p', { style: 'margin: 5px 0; display: flex; align-items: center;' }, [
            h('i', { class: 'el-icon-warning', style: 'color: var(--el-color-warning); margin-right: 8px' }),
            '2.再次提交图片时请刷新页面，防止重复提交之前的图'
          ]),
          h('p', { style: 'margin: 5px 0; display: flex; align-items: center;' }, [
            h('i', { class: 'el-icon-warning', style: 'color: var(--el-color-warning); margin-right: 8px' }),
            '3.手动更改孤立点像素后，会自动保存'
          ])
        ]),
        duration: 4500,
        position: 'top-right',
        type: 'warning',
        style: {
        width: '450px',  // 设置通知框宽度
        padding: '15px'
      },
        onClose: () => {
          currentNotification = null
        }
      })
    },
    onFileChange(file, fileList) {
      this.selectedFiles = fileList
      this.message = ''
    },
    async uploadFiles() {
      if (this.uploading) return
      
      try {
        this.uploading = true
        this.loading = false  // 先重置loading状态
        this.queuePosition = 0  // 重置队列位置
        
        const zip = new JSZip()
        this.selectedFiles.forEach(file => {
          zip.file(file.raw.name, file.raw)
        })

        const content = await zip.generateAsync({ type: 'blob' })
        const formData = new FormData()
        formData.append('file', content, 'files.zip')
        formData.append('white_area_threshold', this.whiteAreaThreshold)
        formData.append('black_area_threshold', this.blackAreaThreshold)

        const { data } = await axios.post(API_URLS.PROCESS, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              this.uploadProgress = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              )
            }
          }
        })

        if (data.status === 'success') {
          this.taskId = data.task_id
          this.loading = true  // 上传成功后设置loading为true
          this.startStatusCheck()
        }
      } catch (error) {
        console.error('上传错误:', error)
        this.message = error.response?.data?.message || '文件处理失败'
        this.alertType = 'error'
        this.zipFile = ''
        this.totalFiles = 0
        this.processedFilesCount = 0
        this.$message.error(this.message)
      } finally {
        this.uploading = false
      }
    },
    async downloadFile() {
      if (!this.zipFile) {
        this.$message.error('没有可下载的文件')
        return
      }

      try {
        const response = await axios.get(`${API_URLS.API_BASE_URL}/api/download/${this.zipFile}`, {
          responseType: 'blob'
        })
        
        const url = URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.download = this.zipFile
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        
        this.$message.success('开始下载')
      } catch (error) {
        console.error('下载错误:', error)
        this.$message.error('下载失败')
      }
    },
    initCustomAnimation() {
      (function () {
        function n(n, e, t) {
          return n.getAttribute(e) || t;
        }
        function e(n) {
          return document.getElementsByTagName(n);
        }
        function t() {
          var t = e("script"),
            o = t.length,
            i = t[o - 1];
          return {
            l: o,
            z: n(i, "zIndex", -1),
            o: n(i, "opacity", 0.5),
            c: n(i, "color", "0,0,0"),
            n: n(i, "count", 99)
          };
        }
        function o() {
          a = m.width =
            window.innerWidth ||
            document.documentElement.clientWidth ||
            document.body.clientWidth;
          c = m.height =
            window.innerHeight ||
            document.documentElement.clientHeight ||
            document.body.clientHeight;
        }
        function i() {
          r.clearRect(0, 0, a, c);
          var n, e, t, o, m, l;
          s.forEach(function (i, x) {
            for (
              i.x += i.xa,
                i.y += i.ya,
                i.xa *= i.x > a || i.x < 0 ? -1 : 1,
                i.ya *= i.y > c || i.y < 0 ? -1 : 1,
                r.fillRect(i.x - 0.5, i.y - 0.5, 1, 1),
                e = x + 1;
              e < u.length;
              e++
            )
              (n = u[e]),
                null !== n.x &&
                  null !== n.y &&
                  ((o = i.x - n.x),
                  (m = i.y - n.y),
                  (l = o * o + m * m),
                  l < n.max &&
                    (n === y &&
                      l >= n.max / 2 &&
                      ((i.x -= 0.03 * o), (i.y -= 0.03 * m)),
                    (t = (n.max - l) / n.max),
                    r.beginPath(),
                    (r.lineWidth = t / 2),
                    (r.strokeStyle = "rgba(" + d.c + "," + (t + 0.2) + ")"),
                    r.moveTo(i.x, i.y),
                    r.lineTo(n.x, n.y),
                    r.stroke()));
          }),
            x(i);
        }
        var a,
          c,
          u,
          m = document.createElement("canvas"),
          d = t(),
          l = "c_n" + d.l,
          r = m.getContext("2d"),
          x =
            window.requestAnimationFrame ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame ||
            window.oRequestAnimationFrame ||
            window.msRequestAnimationFrame ||
            function (n) {
              window.setTimeout(n, 1e3 / 45);
            },
          w = Math.random,
          y = { x: null, y: null, max: 2e4 };
        (m.id = l),
          (m.style.cssText =
            "position:fixed;top:0;left:0;z-index:" +
            d.z +
            ";opacity:" +
            d.o),
          e("body")[0].appendChild(m),
          o(),
          (window.onresize = o),
          (window.onmousemove = function (n) {
            (n = n || window.event), (y.x = n.clientX), (y.y = n.clientY);
          }),
          (window.onmouseout = function () {
            (y.x = null), (y.y = null);
          });
        for (var s = [], f = 0; d.n > f; f++) {
          var h = w() * a,
            g = w() * c,
            v = 2 * w() - 1,
            p = 2 * w() - 1;
          s.push({ x: h, y: g, xa: v, ya: p, max: 6e3 });
        }
        (u = s.concat([y])),
          setTimeout(function () {
            i();
          }, 100);
      })();
    },
    async checkTaskStatus() {
      try {
        const { data } = await axios.get(`${API_URLS.API_BASE_URL}/api/task-status/${this.taskId}`)
        
        if (data.status === TaskStatus.QUEUED) {
          this.queuePosition = data.queue_position
          this.loading = true
        } else if (data.status === TaskStatus.PROCESSING) {
          this.queuePosition = 0
          this.loading = true
        } else if (data.status === TaskStatus.COMPLETED) {
          this.stopStatusCheck()
          this.handleTaskComplete(data.result)
          this.loading = false
        } else if (data.status === TaskStatus.FAILED) {
          this.stopStatusCheck()
          this.handleTaskError(data.error)
          this.loading = false
        }
      } catch (error) {
        console.error('检查任务状态失败:', error)
      }
    },
    startStatusCheck() {
      this.statusCheckInterval = setInterval(() => {
        this.checkTaskStatus()
      }, 1000)
    },
    stopStatusCheck() {
      if (this.statusCheckInterval) {
        clearInterval(this.statusCheckInterval)
        this.statusCheckInterval = null
      }
    },
    handleTaskComplete(result) {
      this.message = result.message
      this.zipFile = result.zip_file
      this.totalFiles = result.total_files
      this.processedFilesCount = result.processed_files_count
      this.alertType = 'success'
    },
    handleTaskError(error) {
      this.message = `处理失败: ${error}`
      this.alertType = 'error'
    }
  },
  beforeUnmount() {
    if (currentNotification) {
      currentNotification.close()
      currentNotification = null
    }
    
    const canvas = document.querySelector('canvas[id^="c_n"]')
    if (canvas) {
      canvas.remove()
    }
    this.stopStatusCheck()
  }
}
</script>

<style scoped>
/* 全局样式，确保通知框样式生效 */
.el-notification {
  min-width: 450px !important;
}

.el-notification__content {
  text-align: left !important;
  word-break: break-all;
  margin: 10px 0 !important;
}
.uploader-container {
  max-width: 800px;
  margin: 0px auto;
  padding: 20px;
}

.box-card {
  border-radius: 15px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  background: linear-gradient(145deg, #ffffff, #f6f7f9);
  border: none;
  overflow: hidden;
  transition: box-shadow 0.3s ease;
}

.box-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}

.card-header {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  padding: 15px 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  position: relative;
}

.tips-button {
  position: absolute;
  right: 20px;
  color: #909399;
  font-size: 14px;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 30px;
  padding: 20px;
}

.upload-section {
  width: 100%;
  max-width: 600px;
}

.upload-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 15px;
}

.threshold-settings {
  width: 100%;
  max-width: 500px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  position: relative;
}

.reset-button {
  position: absolute;
  right: 0;
  color: #909399;
  font-size: 14px;
}

.form-group {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.form-group:last-child {
  border-bottom: none;
}

.form-group label {
  font-weight: 500;
  color: #606266;
}

.status-container {
  margin: 20px 0;
  min-height: 100px;
}

.processing-status {
  padding: 30px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.processing-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.processing-icon {
  color: var(--el-color-primary);
  animation: rotate 2s linear infinite;
}

.processing-text {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.processing-subtext {
  font-size: 14px;
  color: #909399;
}

.result-card {
  margin-top: 20px;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.success-icon {
  color: var(--el-color-success);
}

.error-icon {
  color: var(--el-color-danger);
}

.download-card {
  margin-top: 20px;
  text-align: center;
}

.download-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.download-tip {
  color: #909399;
  font-size: 14px;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .form-group {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  :deep(.el-input-number) {
    width: 100%;
  }
}

.queue-icon {
  color: var(--el-color-warning);
}

.queue-text {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.queue-position {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}
</style>