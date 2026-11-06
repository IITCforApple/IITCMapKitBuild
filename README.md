# IITCMapKitBuild

公开的 macOS arm64 构建入口。`iitc_mapkit` 子模块固定私有仓库提交，不公开源码，也不改变源码授权。

## 首次配置

在 Settings → Secrets and variables → Actions 添加下列 Repository secrets（也支持放在 `Build` Environment secrets）：

| Secret | 内容 |
| --- | --- |
| `IITCMAPKIT_READ_TOKEN` | 可以读取 `chewnglow/iitc_mapkit` 的 fine-grained PAT，Contents: read；需要该仓库所属账号授权 |
| `ARTIFACT_PASSWORD` | 仅用于加密诊断日志的独立长密码 |
| `MACOS_CERTIFICATE_P12_BASE64` | 包含私钥的 Developer ID Application `.p12` 文件的单行 Base64 |
| `MACOS_CERTIFICATE_PASSWORD` | 上述 `.p12` 的导出密码 |
| `NOTARY_APPLE_ID` | Apple Developer 账号的 Apple ID |
| `NOTARY_APP_PASSWORD` | 上述账号的 App 专用密码 |
| `SIGNING_IDENTITY` | 完整证书名称，如 `Developer ID Application: Your Name (TEAMID)` |
| `SIGNING_TEAM_ID` | 对应 Developer Team ID |

后六项可使用 InblessBuild 相同的配置值；签名 identity/team 支持 **Secrets 或 Variables**（Secrets 优先）。GitHub 已保存的 Secrets 无法读回，需要重新从原始凭据填入。不要将凭据提交到 Git 或贴到 Issue。

配置完成后，Actions → Private source build → Run workflow。推送 main 也自动触发。首次未配置 Secrets 时会明确失败，不上传安装包或明文日志。

## 构建和交付

使用 GitHub `xcode-27` Apple Silicon runner（目前为 preview），遵循源码要求的 macOS 27 SDK，并安装 Metal Toolchain。构建 macOS 应用及 Safari 扩展，验证签名和搬移后的资源加载，提交 Apple 公证、装订并验证 App 票据，再创建 ZIP 和 DMG。DMG 也签名、公证、装订并验证。Gatekeeper 检查失败即拒绝收集安装包。

每次成功构建上传五个独立 Actions artifacts，均保留 7 天：

- `IITCMapKit-macos-arm64-logs-encrypted`：仅包含 AES-256、加密文件名的 `IITCMapKit-macos-arm64-logs.7z`。解密后只有 `logs/`（包括源码提交记录），不包含 `packages/`。用 7-Zip 和 `ARTIFACT_PASSWORD` 解密。
- `IITC-Native-<version>-macOS-arm64.zip`：不加密的应用 ZIP。
- `IITC-Native-<version>-macOS-arm64.zip.sha256`：不加密的 ZIP 校验和。
- `IITC-Native-<version>-macOS-arm64.dmg`：不加密的 DMG。
- `IITC-Native-<version>-macOS-arm64.dmg.sha256`：不加密的 DMG 校验和。

四个公开产物各只上传对应文件，不上传整个输出目录。只有构建、签名、公证及验证全部成功后才上传安装包和校验和；失败时仅尝试上传加密日志。安装包可公开下载，无需密码；日志内容继续保密。

私有构建日志不打印到公开 Actions 页面；源码仓库地址、固定提交、构建阶段和工具安装信息仍可见。不配置 PR 触发、不缓存私有源码和编译产物、不自动发布 Release。签名私钥和公证凭据在临时 keychain 中使用并清理。仅使用 GitHub 托管 runner。

iOS 构建和 TestFlight 不在此流程中；Apple 公证针对 macOS 分发。本仓库完成配置不等于公证验收：需要首次 Actions 实际完成且产物通过检查。

## 更新固定源码

```sh
git submodule update --init
git -C iitc_mapkit fetch origin
git -C iitc_mapkit checkout <reviewed-commit>
git add iitc_mapkit
git commit -m 'build: 更新 IITCMapKit 源码版本'
git push
```

## 参考

- [Apple 公证流程](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [GitHub runner 标签与工具链](https://github.com/actions/runner-images)
