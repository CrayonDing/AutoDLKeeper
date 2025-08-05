# -- coding: utf-8 --
import requests
import time

def process_account(phone, password):
    """处理单个账号的所有实例，排除name为AutoDLKeeper的实例"""
    print(f"\n{'='*50}")
    print(f"开始处理账号: {phone}")
    print(f"{'='*50}")
    
    # 1. POST请求获取登录失败计数
    print("步骤1: 获取登录失败计数")
    login_failed_url = "https://www.autodl.com/api/v1/login_failed/count"
    login_failed_params = {"phone": phone}
    
    try:
        response = requests.post(login_failed_url, json=login_failed_params)
        response_data = response.json()
        print(f"登录失败计数返回: {response_data}")
    except Exception as e:
        print(f"步骤1执行失败: {str(e)}")
        return False
    
    # 2. POST请求登录获取ticket
    print("\n步骤2: 登录获取ticket")
    login_url = "https://www.autodl.com/api/v1/new_login"
    login_params = {
        "phone": phone,
        "password": password,
        "v_code": "",
        "phone_area": "+86",
        "picture_id": None
    }

    try:
        response = requests.post(login_url, json=login_params)
        login_data = response.json()
        print(f"登录请求返回: {login_data.get('code')}")
        if login_data.get("code") == "Success":
            ticket = login_data.get("data", {}).get("ticket")
            if not ticket:
                print("无法提取ticket")
                return False
            print(f"提取到ticket: {ticket}")
        else:
            print(f"登录失败，错误代码: {login_data.get('code')}")
            return False
    except Exception as e:
        print(f"步骤2执行失败: {str(e)}")
        return False
    
    # 3. 使用ticket获取token
    print("\n步骤3: 使用ticket获取token")
    passport_url = "https://www.autodl.com/api/v1/passport"
    passport_params = {"ticket": ticket}
    
    try:
        response = requests.post(passport_url, json=passport_params)
        passport_data = response.json()
        print(f"获取token返回: {passport_data}")
        
        token = passport_data.get("data", {}).get("token")
        if not token:
            print("无法提取token")
            return False
        print(f"提取到token: {token}")
    except Exception as e:
        print(f"步骤3执行失败: {str(e)}")
        return False
    
    # 设置请求头，包含token
    headers = {"authorization": token}
    
    # 4. 获取所有实例列表
    print("\n步骤4: 获取所有实例列表")
    instances_url = "https://www.autodl.com/api/v1/instance"
    instances_params = {
        "date_from": "",
        "date_to": "",
        "page_index": 1,
        "page_size": 100,
        "status": [],
        "charge_type": []
    }
    
    try:
        response = requests.get(instances_url, params=instances_params, headers=headers)
        instances_data = response.json()
        total_instances = instances_data.get("data").get("result_total")
        print(f"实例列表返回: 共{total_instances}个实例")
        
        instances_list = instances_data.get("data", {}).get("list", [])
        if not instances_list:
            print("未找到任何实例")
            return True
        
        # 提取所有实例的UUID，排除name为AutoDLKeeper的实例
        filtered_instances = [
            instance for instance in instances_list 
            if instance.get("uuid") and instance.get("name") != "AutoDLKeeper"
        ]
        
        excluded_count = len(instances_list) - len(filtered_instances)
        if excluded_count > 0:
            print(f"已排除 {excluded_count} 个name为AutoDLKeeper的实例")
            
        instance_uuids = [instance.get("uuid") for instance in filtered_instances]
        print(f"提取到{len(instance_uuids)}个符合条件的实例UUID: {instance_uuids}")
    except Exception as e:
        print(f"步骤4执行失败: {str(e)}")
        return False
    
    # 5. 依次处理每个实例
    print("\n步骤5: 开始处理每个实例")
    power_on_url = "https://www.autodl.com/api/v1/instance/power_on"
    power_off_url = "https://www.autodl.com/api/v1/instance/power_off"
    
    for index, uuid in enumerate(instance_uuids, 1):
        print(f"\n处理第{index}/{len(instance_uuids)}个实例，UUID: {uuid}")
        
        # 发送开机请求
        print(f"发送开机请求到实例 {uuid}")
        try:
            power_on_params = {
                "instance_uuid": uuid,
                "payload": "non_gpu"
            }
            response = requests.post(power_on_url, json=power_on_params, headers=headers)
            power_on_data = response.json()
            print(f"开机请求返回: {power_on_data}")
        except Exception as e:
            print(f"发送开机请求失败: {str(e)}")
            continue
        
        # 循环检查实例状态
        instance_status = None
        max_checks = 20  # 最大检查次数，防止无限循环
        check_count = 0
        
        while check_count < max_checks:
            check_count += 1
            print(f"第{check_count}次检查实例 {uuid} 状态")
            
            # 获取实例状态
            try:
                response = requests.get(instances_url, params=instances_params, headers=headers)
                status_data = response.json()
                # 找到当前实例的状态
                for instance in status_data.get("data", {}).get("list", []):
                    if instance.get("uuid") == uuid:
                        instance_status = instance.get("status")
                        print(f"实例 {uuid} 当前状态: {instance_status}")
                        break
            except Exception as e:
                print(f"获取实例状态失败: {str(e)}")
                time.sleep(3)
                continue
            
            # 检查状态并执行相应操作
            if instance_status == "running":
                print(f"实例 {uuid} 已运行，发送关机请求")
                try:
                    power_off_params = {"instance_uuid": uuid}
                    response = requests.post(power_off_url, json=power_off_params, headers=headers)
                    power_off_data = response.json()
                    print(f"关机请求返回: {power_off_data}")
                except Exception as e:
                    print(f"发送关机请求失败: {str(e)}")
                # 这里不写break跳出，而是让他再检查一轮，直到shutdown状态或者超时再退出
            elif instance_status == "starting":
                print(f"实例 {uuid} 正在启动，3秒后再次检查")
                time.sleep(3)
            elif instance_status == "shutdown":
                print(f"实例 {uuid} 已关机，开始处理下一个实例")
                #进入下一实例处理
                break
            else:
                print(f"实例 {uuid} 处于未知状态: {instance_status}，3秒后再次检查")
                time.sleep(3)
        
        if check_count >= max_checks:
            print(f"达到最大检查次数，实例 {uuid} 处理超时")
    
    print(f"\n账号 {phone} 的所有实例处理完毕")
    return True

def main():
    # 在这里定义多个账号，格式：(手机号, 密码)
    # token可在登录页面抓包new_login的参数部分查看
    accounts = [
        ("phone1", "token1"),
        ("phone2", "token2"),  # 取消注释添加更多账号
    ]
    
    print(f"开始处理 {len(accounts)} 个账号")
    
    success_count = 0
    failed_count = 0
    
    # 依次处理每个账号
    for i, (phone, password) in enumerate(accounts, 1):
        print(f"\n处理第 {i}/{len(accounts)} 个账号")
        
        if process_account(phone, password):
            success_count += 1
        else:
            failed_count += 1
        
        # 账号之间添加延迟，避免请求过于频繁
        if i < len(accounts):
            print(f"\n等待5秒后处理下一个账号...")
            time.sleep(5)
    
    print(f"\n{'='*50}")
    print(f"处理完成！成功: {success_count} 个账号，失败: {failed_count} 个账号")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
