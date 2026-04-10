Olivetti Faces（AT&T Cambridge）
- 约 400 张灰度人脸，40 人，每人 10 张，像素 64x64。
- sklearn 缓存: E:\File\travel_manager_ga\travel_manager\travel_manager\offline\data\face_datasets\sklearn_cache
- 按人导出的 PNG: E:\File\travel_manager_ga\travel_manager\travel_manager\offline\data\face_datasets\olivetti_export（person_XX/00.png ..）

Python 加载示例:
  from sklearn.datasets import fetch_olivetti_faces
  d = fetch_olivetti_faces(data_home='E:\\File\\travel_manager_ga\\travel_manager\\travel_manager\\offline\\data\\face_datasets\\sklearn_cache')
  X, y, imgs = d.data, d.target, d.images  # X 用于 NB+PCA；imgs 用于 CNN

扁平形状: (400, 4096), 图像形状: (400, 64, 64), 类别数: 40
