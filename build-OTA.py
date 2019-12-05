import json
import binascii


filename = 'OTA_CLUSTER.json'

"""
<LHHHHHLH32BLBQHH
Header[0:69]:
                                           IKEA             LEDVANCE       LEGRAND
    Long   ==> file_id                     0xbeef11e        0xbeef11e
    Ushort ==> header_version              0x100            0x100
    Ushort ==> header_lenght               0x38             0x38
    Ushort ==> header_fctl                 0x0              0x0

    Ushort ==> manufacturer_code:          0x117c           0x1189         0x1021
    Ushort ==> image_type:                                                 see Definition below
    Long   ==> image_version                                               0x00204103 
                                                                             xx -------- Application release 0x00
                                                                               xx ------ Application Build   0x20 ( 32 )
                                                                                 xx ---- Stack release       0x41 ( 65 )
                                                                                   xx -- Stack Build         0x03 ( 03 )
    Ushort ==> stack_version               0x2              0x2            0x3

    32uchar => header_str
    Long   ==> size: => Size of the file
    Uchar  ==> security_cred_version       0x0              0x0
    Ulonglong> upgrade_file_dest
    Ushort ==> min_hw_version
    Ushort ==> max_hw_version
    """

IMAGE_TYPES = {
        # 0xffff stand for unknown at that stage
        'Cable outlet': 0xffff,
        'Connected outlet': 0x0011,
        'Dimmer switch w/o neutral': 0x000e,
        'Shutter switch with neutral': 0x0013,
        'Micromodule switch': 0x0010,
        'Remote switch': 0xffff,
        'Double gangs remote switch': 0x0016,
        'Shutters central remote switch': 0xffff
        }


firmware = {}
last_offset = 0
last_sqn = 0

with open( filename, 'r') as f:
    array = json.load(f)


for item in array:
    if '_source' not in item:
        continue
    if 'layers' not in item['_source']:
        continue
    if 'zbee_aps' not in item['_source']['layers']:
        continue
    if 'zbee_aps.cluster' not in item['_source']['layers']['zbee_aps']:
        continue

    if 'zbee_zcl' not in item['_source']['layers']:
        continue

    if 'zbee_zcl.cmd.tsn' in item['_source']['layers']['zbee_zcl']:
        if last_sqn + 1 <  int( item['_source']['layers']['zbee_zcl']['zbee_zcl.cmd.tsn']):
            print("====> Lost in Sequence %s versus %s" %(last_sqn, int(item['_source']['layers']['zbee_zcl']['zbee_zcl.cmd.tsn'])))
        last_sqn = int(item['_source']['layers']['zbee_zcl']['zbee_zcl.cmd.tsn'])

    if item['_source']['layers']['zbee_aps']['zbee_aps.cluster'] != '25': # We are looking only for Cluster 0x19
        continue

    if 'zbee_zcl_general.ota.cmd.srv_rx.id' in item['_source']['layers']['zbee_zcl']:
        if item['_source']['layers']['zbee_zcl']['zbee_zcl_general.ota.cmd.srv_rx.id'] == '0x00000001':
            # Query Next Image Request 
            manuf_code = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.manufacturer_code']
            image_type = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.type']
            file_version = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.file.version']
            print("0x01 - ManufCode: %s, Type: %s, Version: %s" %(manuf_code, image_type, file_version ))

        elif item['_source']['layers']['zbee_zcl']['zbee_zcl_general.ota.cmd.srv_rx.id'] == '0x00000004':
            manuf_code = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.manufacturer_code']
            image_type = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.type']
            file_version = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.file.version']

            offset = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.file.offset']
            data_size = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.max_data_size']
            page_size = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.page.size']
            rsp_spacing = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.rsp_spacing']

            ###print("0x04 - ManufCode: %s, Type: %s, Version: %s, Offset: %s, Dsize: %s, Psize: %s, RspSpace: %s" %(manuf_code, image_type, file_version, offset, data_size,page_size, rsp_spacing))


    elif 'zbee_zcl_general.ota.cmd.srv_tx.id' in item['_source']['layers']['zbee_zcl']:
        if item['_source']['layers']['zbee_zcl']['zbee_zcl_general.ota.cmd.srv_tx.id'] == '0x00000002':
            if item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.status'] == '0x00000000':
                manuf_code = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.manufacturer_code']
                image_type = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.type']
                file_version = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.file.version']
                file_size = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.size']
    
                print("New Firmware to be captured: Manuf: %s, Type: %s, Version: %s, Size: %s" %(manuf_code, image_type, file_version, file_size))
                if image_type not in firmware:
                    last_offset = 0
                    firmware[image_type] = {}
                    firmware[image_type]['Version'] = file_version
                    firmware[image_type]['Image'] = {}
                    firmware[image_type]['Size'] = file_size
                else:
                    print("========>   Something wrong ... already existing ....")
            else:
                print("===> Status not 0x00: %s" %item['_source']['layers']['zbee_zcl'])


        if item['_source']['layers']['zbee_zcl']['zbee_zcl_general.ota.cmd.srv_tx.id'] == '0x00000005':
            manuf_code = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.manufacturer_code']
            image_type = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.type']
            file_version = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.file.version']

            Offset = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.file.offset']
            DataSize = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.data_size']

            cwdata_raw = None
            if 'zbee_zcl_general.ota.image.data_raw' in item['_source']['layers']['zbee_zcl']['Payload']:
                if len(item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.data_raw'][0]) != (int(DataSize) * 2):
                    print("Not matching size - Data len: %s expecting %s" %(len(item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.data_raw'][0]), int(DataSize)*2))
                    print("%s" %item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.data_raw'][0])
                else:
                    cwdata_raw = item['_source']['layers']['zbee_zcl']['Payload']['zbee_zcl_general.ota.image.data_raw'][0]
                    print("0x05 - [%3s]  ManufCode: %s, Type: %s, Version: %s, Offset: %s Size: %s" %(last_sqn, manuf_code, image_type, file_version, Offset, DataSize ))
            else:
                continue
                #print("Missing raw payload: %s" %item['_source']['layers']['zbee_zcl'])

            if image_type not in firmware:
                last_offset = 0
                firmware[image_type] = {}
                firmware[image_type]['Version'] = file_version
                firmware[image_type]['Image'] = {}
            if 'Image' not in firmware[image_type]:
                firmware[image_type]['Image'] = {}

            if firmware[image_type]['Version'] != file_version:
                print("Error missmatch of Version %s versus %s" %(firmware[image_type]['Version'], file_version))
                continue
            if cwdata_raw:
                if last_offset + 64 != int( Offset):
                    print("Last Offset: %s new Offset: %s ==> Gap: %s" %(last_offset, Offset, int(Offset) - last_offset))
                last_offset = int(Offset)
                if len(cwdata_raw) == 2*int(DataSize) and Offset not in firmware[image_type]['Image']:
                    firmware[image_type]['Image'][Offset] = cwdata_raw
                else:
                    print("-----> DEDUP - Offset: %s already loaded" %(Offset))
                    continue



for firm in firmware:
    print("Captured firmware:")
    print("--> Type   : %s" %firm)
    print("--> Version: %s" %firmware[firm]['Version'])
    print("--> Size   : %s" %firmware[firm]['Size'])
    print("--> Chunk  : %s" %len(firmware[firm]['Image']))
